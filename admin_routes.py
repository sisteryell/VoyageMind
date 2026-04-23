"""Admin routes for managing the RAG country collection.

All endpoints require a valid ``X-Admin-Key`` header that matches the
``ADMIN_API_KEY`` environment variable.  An empty or unset key rejects
every request.
"""

import hmac

from config import get_settings
from controllers.rag_controller import add_entries, delete_all, delete_entry, edit_entry, list_entries
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import APIKeyHeader
from middleware import limiter
from schemas import RAGAddRequest, RAGAddResponse, RAGEditRequest, RAGEntryOut, RAGListResponse


_api_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


async def admin_required(api_key: str | None = Depends(_api_key_header)) -> None:
    """Reject requests that lack a valid admin key."""
    settings = get_settings()
    expected = settings.admin_api_key
    if not expected:
        raise HTTPException(status_code=403, detail="Admin access is disabled")
    if api_key is None or not hmac.compare_digest(api_key, expected):
        raise HTTPException(status_code=403, detail="Invalid admin key")


admin_router = APIRouter(
    prefix="/admin/rag",
    tags=["admin"],
    dependencies=[Depends(admin_required)],
)


@admin_router.post("/entries", response_model=RAGAddResponse)
@limiter.limit("10/minute")
async def add_entries_controller(request: Request, body: RAGAddRequest):
    return await add_entries(body)


@admin_router.get("/entries", response_model=RAGListResponse)
@limiter.limit("10/minute")
async def list_entries_controller(request: Request, limit: int = Query(20, ge=1, le=200), offset: int = Query(0, ge=0)):
    return await list_entries(limit=limit, offset=offset)


@admin_router.put("/entries/{entry_id}", response_model=RAGEntryOut)
@limiter.limit("10/minute")
async def edit_entry_controller(request: Request, entry_id: str, body: RAGEditRequest):
    return await edit_entry(entry_id=entry_id, body=body)


@admin_router.delete("/entries/{entry_id}", response_model=RAGEntryOut)
@limiter.limit("10/minute")
async def delete_entry_controller(request: Request, entry_id: str):
    return await delete_entry(entry_id=entry_id)

@admin_router.delete("/entries", response_model=None)
@limiter.limit("10/minute")
async def delete_all_controller(request: Request):
    return await delete_all()