"""Controller handlers for RAG endpoints."""

from __future__ import annotations
import logging
from fastapi import HTTPException
from rag_service import CountryRAGService
from schemas import RAGAddRequest, RAGAddResponse, RAGEditRequest, RAGEntryOut, RAGListResponse

logger = logging.getLogger(__name__)


def _rag() -> CountryRAGService:
    """Return the initialized RAG singleton, or raise 503 if unavailable."""

    rag = CountryRAGService.get_instance()
    if not rag._initialized:
        raise HTTPException(status_code=503, detail="RAG service is not initialized")
    return rag

async def add_entries(body: RAGAddRequest) -> RAGAddResponse:
    rag = _rag()
    result = rag.add_entries(body.entries)

    added_entries = []
    for e in result["added"]:
        added_entries.append(RAGEntryOut(**e))

    existing_entries = []
    for e in result["already_exist"]:
        existing_entries.append(RAGEntryOut(**e))

    return RAGAddResponse(
        added=added_entries,
        already_exist=existing_entries,
    )

async def list_entries(limit: int = 20, offset: int = 0) -> RAGListResponse:
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 200")
    if offset < 0:
        raise HTTPException(status_code=422, detail="offset must be non-negative")

    rag = _rag()
    result = rag.list_entries(limit=limit, offset=offset)
    entries_list = []
    for e in result["entries"]:
        entry_obj = RAGEntryOut(**e)
        entries_list.append(entry_obj)

    return RAGListResponse(
        entries=entries_list,
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )

async def edit_entry(entry_id: str, body: RAGEditRequest) -> RAGEntryOut:
    rag = _rag()
    result = rag.edit_entry(
        entry_id=entry_id,
        variant=body.variant,
        alpha2=body.country_code,
    )

    if result is None:
        raise HTTPException(status_code=404, detail=f"Entry '{entry_id}' not found")

    return RAGEntryOut(**result)

async def delete_entry(entry_id: str) -> RAGEntryOut:
    rag = _rag()
    result = rag.delete_entry(entry_id=entry_id)

    if result is None:
        raise HTTPException(status_code=404, detail=f"Entry '{entry_id}' not found")

    return RAGEntryOut(**result)

async def delete_all() -> dict:
    rag = _rag()
    count = rag.delete_all()
    return {"deleted_count": count}