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

    # 3. Recover and evaluate any pending submissions left over from previous starts
    from core.database import AsyncSessionFactory, Submission, SubmissionStatus
    from sqlalchemy import select
    from services.orchestrator import run_evaluation
    try:
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(Submission).where(Submission.status == SubmissionStatus.pending)
            )
            pending_subs = result.scalars().all()
            if pending_subs:
                logger.info(f"Found {len(pending_subs)} pending submissions on startup. Launching sequential recovery worker...")
                async def run_recovery():
                    for sub in pending_subs:
                        try:
                            await run_evaluation(sub.id)
                            # Sleep to respect Gemini's 15 RPM / 20 RPM free tier limits
                            await asyncio.sleep(10.0)
                        except Exception as e:
                            logger.error(f"Recovery evaluation failed for {sub.id}: {e}")
                asyncio.create_task(run_recovery())
    except Exception as e:
        logger.error(f"Failed to recover pending submissions: {e}")

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
