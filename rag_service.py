"""RAG service for country name resolution using ChromaDB and OpenAI embeddings.

Provides semantic similarity search over a comprehensive corpus of country
names, abbreviations, and informal aliases.  Designed as a fallback tier
when exact-match and fuzzy-search cannot resolve user input.
"""

from __future__ import annotations

import hashlib
import logging
from threading import Lock
from typing import Any

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

from config import get_settings
from country_data import build_country_corpus

logger = logging.getLogger(__name__)

_COLLECTION_NAME = "country_names"


class CountryRAGService:
    """Thread-safe singleton that wraps a ChromaDB collection of country name embeddings."""

    _instance: CountryRAGService | None = None
    _lock = Lock()
    _initialized: bool = False

    def __new__(cls) -> CountryRAGService:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    cls._instance = inst
        return cls._instance

    def initialize(self) -> None:
        """Create or load the ChromaDB collection, populating it on first run.

        Safe to call multiple times — skips work if already initialized.
        """
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return
            self._setup()
            self._initialized = True

    def _setup(self) -> None:
        settings = get_settings()

        self._embedding_fn = OpenAIEmbeddingFunction(
            api_key=settings.openai_api_key,
            model_name=settings.openai_embedding_model,
        )
        self._threshold = settings.rag_similarity_threshold

        self._client = chromadb.PersistentClient(
            path=settings.rag_persist_directory,
        )

        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            embedding_function=self._embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

        if self._collection.count() == 0:
            self._populate()

    def _populate(self) -> None:
        """Embed and store the full country corpus."""
        corpus = build_country_corpus()
        if not corpus:
            logger.warning("Country corpus is empty — skipping RAG population")
            return

        batch_size = 100
        for i in range(0, len(corpus), batch_size):
            batch = corpus[i : i + batch_size]
            ids = [f"country_{i + j}" for j in range(len(batch))]
            documents = [variant for variant, _ in batch]
            metadatas = [{"canonical_name": canonical} for _, canonical in batch]

            self._collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )

        logger.info("RAG collection populated with %d country name variants", len(corpus))

    def resolve_country(self, query: str) -> str | None:
        """Search for the closest matching country name.

        Returns the canonical country name if the best result meets the
        similarity threshold, otherwise ``None``.
        """
        if not self._initialized:
            logger.warning("RAG service not initialized — skipping lookup")
            return None

        query = query.strip()
        if not query:
            return None

        try:
            results: dict[str, Any] = self._collection.query(
                query_texts=[query],
                n_results=1,
                include=["metadatas", "distances"],
            )
        except Exception:
            logger.warning("RAG query failed for '%s'", query, exc_info=True)
            return None

        if not results["ids"] or not results["ids"][0]:
            return None

        distance = results["distances"][0][0]
        if distance > self._threshold:
            logger.debug(
                "RAG match for '%s' below threshold (distance=%.4f, threshold=%.4f)",
                query, distance, self._threshold,
            )
            return None

        return results["metadatas"][0][0]["canonical_name"]

    @staticmethod
    def _variant_id(normalized_version: str) -> str:
        """Derive a deterministic ID from a normalized variant string."""
        return f"c_{hashlib.sha256(normalized_version.encode()).hexdigest()[:16]}"

    def _find_by_variant(self, normalized_variant: str) -> str | None:
        """Return the existing entry ID if the variant is already in the collection."""
        country_id = self._variant_id(normalized_version=normalized_variant)
        existing = self._collection.get(ids=[country_id])
        if existing["ids"]:
            return country_id

        try:
            search = self._collection.get(
                where_document={"$contains": normalized_variant},
                include=["documents"],
            )
            for doc_id, doc in zip(search["ids"], search["documents"]):
                if doc == normalized_variant:
                    return doc_id
        except Exception:
            logger.warning(f"Variant search failed for {normalized_variant}", exc_info=True)

        return None

    def add_entries(self, entries: dict[str, str]) -> dict[str, list[dict]]:
        import pycountry

        added: list[dict[str, str]] = []
        already_exist: list[dict[str, str]] = []

        for variant, alpha2 in entries.items():
            normalized = variant.strip().lower()
            country = pycountry.countries.get(alpha_2=alpha2)
            canonical = alpha2
            if country:
                canonical = country.name

            existing_id = self._find_by_variant(normalized_variant=normalized)
            if existing_id:
                already_exist.append(
                    {"id": existing_id, "variant": normalized, "canonical_name": canonical}
                )
                continue

            entry_id = self._variant_id(normalized_version=normalized)
            self._collection.add(
                ids=[entry_id],
                documents=[normalized],
                metadatas=[{"canonical_name": canonical}],
            )
            added.append({"id": entry_id, "variant": normalized, "canonical_name": canonical})

        logger.info(f"RAG add_entries: {len(added)} added, {len(already_exist)} duplicates")
        return {"added": added, "already_exist": already_exist}
    
    def edit_entry(self, entry_id: str, variant: str, alpha2: str) -> dict[str, str] | None:
        import pycountry

        existing = self._collection.get(ids=[entry_id])
        if not existing["ids"]:
            return None

        country = pycountry.countries.get(alpha_2=alpha2)
        normalized = variant.strip().lower()
        canonical = alpha2
        if country:
            canonical = country.name

        self._collection.update(
            ids=[entry_id],
            documents=[normalized],
            metadatas=[{"canonical_name": canonical}],
        )

        logger.info(f"RAG entry updated: {entry_id} -> {normalized} ({canonical})")
        return {"id": entry_id, "variant": normalized, "canonical_name": canonical}

    def delete_entry(self, entry_id: str) -> dict[str, str] | None:
        existing = self._collection.get(
            ids=[entry_id], include=["documents", "metadatas"]
        )

        if not existing["ids"]:
            return None

        deleted = {
            "id": entry_id,
            "variant": existing["documents"][0],
            "canonical_name": existing["metadatas"][0]["canonical_name"],
        }
        self._collection.delete(ids=[entry_id])

        logger.info(f"RAG entry deleted: {entry_id} ({deleted['variant']})")
        return deleted

    def list_entries(self, limit: int = 20, offset: int = 0) -> dict:
        total = self._collection.count()
        results = self._collection.get(
            include=["documents", "metadatas"],
            limit=limit,
            offset=offset,
        )

        entries = []
        for i in range(len(results["ids"])):
            entry = {
                "id": results["ids"][i],
                "variant": results["documents"][i],
                "canonical_name": results["metadatas"][i]["canonical_name"],
            }
            entries.append(entry)

        return {"entries": entries, "total": total, "limit": limit, "offset": offset}

    def delete_all(self) -> int:
        count = self._collection.count()
        if count == 0:
            return 0

        self._client.delete_collection(_COLLECTION_NAME)
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            embedding_function=self._embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"RAG collection wiped: {count} entries removed")
        return count

    @classmethod
    def get_instance(cls) -> CountryRAGService:
        """Return the singleton instance."""
        return cls()