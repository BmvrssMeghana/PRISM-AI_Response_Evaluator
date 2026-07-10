"""
PRISM — FastAPI Application Entry Point
"""
import asyncio
import logging
import sys
import os
from contextlib import asynccontextmanager

# Force UTF-8 stdout/stderr on Windows to avoid cp1252 UnicodeEncodeErrors
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.database import init_db
from api.routes.submissions import router as submissions_router
from api.routes.knowledge import router as knowledge_router

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ── Lifespan ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB tables + kick off ingestion in background."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # 1. Create PostgreSQL tables
    await init_db()
    logger.info("Database tables ready [OK]")

    # 2. Start ingestion in background (non-blocking)
    from ingestion.pipeline import run_ingestion_async
    sources = [s.strip() for s in settings.INGEST_SOURCES.split(",")]
    logger.info(f"Launching background ingestion for: {sources}")
    asyncio.create_task(run_ingestion_async(sources))

    yield

    logger.info(f"PRISM shutting down ...")


# ── App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="PRISM — AI Response Evaluator API",
    description="Reference Knowledge Base and Evaluation Input Module",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS — allow React dev server ────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────
app.include_router(submissions_router)
app.include_router(knowledge_router)


# ── Health check ─────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/", tags=["system"])
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "docs": "/docs",
        "health": "/health",
    }
