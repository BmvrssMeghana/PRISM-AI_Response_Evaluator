"""
PRISM — Knowledge Base API Routes
GET /api/kb/retrieve  — Semantic search over the reference KB
GET /api/kb/stats     — Collection statistics
GET /api/kb/status    — Ingestion readiness check
"""
import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from core.vector_store import get_collection_stats, count_documents
from core.config import settings
from retrieval.retriever import retrieve

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/kb", tags=["knowledge-base"])


# ── GET /api/kb/retrieve ─────────────────────────────────────────────
@router.get("/retrieve")
async def retrieve_chunks(
    question: str = Query(..., min_length=3, description="Question to search for"),
    k: int = Query(5, ge=1, le=20, description="Number of top chunks to return"),
):
    if count_documents() == 0:
        raise HTTPException(
            503,
            "Knowledge base is empty. Ingestion may still be running — try again in a few minutes.",
        )

    loop = asyncio.get_event_loop()
    try:
        results = await loop.run_in_executor(None, retrieve, question, k)
    except Exception as e:
        logger.error(f"Retrieval error: {e}")
        raise HTTPException(500, f"Retrieval failed: {str(e)}")

    return {
        "question": question,
        "k": k,
        "results": results,
    }


# ── GET /api/kb/stats ────────────────────────────────────────────────
@router.get("/stats")
async def kb_stats():
    loop = asyncio.get_event_loop()
    stats = await loop.run_in_executor(None, get_collection_stats)
    return stats


# ── GET /api/kb/status ───────────────────────────────────────────────
@router.get("/status")
async def kb_status():
    count = count_documents()
    ready = count >= settings.INGEST_MIN_DOCS
    return {
        "ready": ready,
        "chunk_count": count,
        "min_required": settings.INGEST_MIN_DOCS,
        "message": "Knowledge base ready" if ready else "Ingestion in progress or not started",
    }
