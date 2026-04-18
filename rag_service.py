"""RAG service for country name resolution using ChromaDB and OpenAI embeddings.

Provides semantic similarity search over a comprehensive corpus of country
names, abbreviations, and informal aliases.  Designed as a fallback tier
when exact-match and fuzzy-search cannot resolve user input.
"""

from __future__ import annotations

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

    @classmethod
    def get_instance(cls) -> CountryRAGService:
        """Return the singleton instance."""
        return cls()