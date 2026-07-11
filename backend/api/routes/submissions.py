"""
PRISM — Submissions API Routes
POST /api/submit    — Create a new evaluation submission
GET  /api/submissions       — List all submissions (paginated)
GET  /api/submissions/{id}  — Get a single submission
"""
import uuid
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.database import get_db, Submission, SubmissionStatus
from services.orchestrator import run_evaluation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["submissions"])

MAX_QUESTION_LEN = 5000
MAX_RESPONSE_LEN = 10000
MAX_REFERENCE_LEN = 8000
MAX_FILE_SIZE_MB = 10


def _extract_pdf_text(content: bytes, filename: str) -> str:
    """Extract text from PDF bytes using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        import io
        doc = fitz.open(stream=io.BytesIO(content), filetype="pdf")
        pages = []
        for page in doc:
            pages.append(page.get_text())
        doc.close()
        return "\n\n".join(pages).strip()
    except Exception as e:
        logger.error(f"PDF extraction failed for {filename}: {e}")
        return ""


def _extract_txt_text(content: bytes) -> str:
    """Decode plain-text file."""
    try:
        return content.decode("utf-8", errors="replace").strip()
    except Exception:
        return ""


# ── POST /api/submit ─────────────────────────────────────────────────
@router.post("/submit", status_code=201)
async def submit_evaluation(
    question: str = Form(..., description="The question asked to the AI"),
    ai_response: str = Form(..., description="The AI-generated answer to evaluate"),
    reference_answer: Optional[str] = Form(None, description="Optional reference/ground-truth answer"),
    file: Optional[UploadFile] = File(None, description="Optional PDF or TXT reference document"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
):
    # ── Validate lengths ────────────────────────────────────────────
    if len(question) > MAX_QUESTION_LEN:
        raise HTTPException(422, f"Question exceeds {MAX_QUESTION_LEN} characters")
    if len(ai_response) > MAX_RESPONSE_LEN:
        raise HTTPException(422, f"AI response exceeds {MAX_RESPONSE_LEN} characters")
    if reference_answer and len(reference_answer) > MAX_REFERENCE_LEN:
        raise HTTPException(422, f"Reference answer exceeds {MAX_REFERENCE_LEN} characters")

    question = question.strip()
    ai_response = ai_response.strip()
    if not question:
        raise HTTPException(422, "Question cannot be empty")
    if not ai_response:
        raise HTTPException(422, "AI response cannot be empty")

    # ── Handle file upload ──────────────────────────────────────────
    doc_text: Optional[str] = None
    doc_filename: Optional[str] = None

    if file and file.filename:
        content = await file.read()
        size_mb = len(content) / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            raise HTTPException(413, f"File exceeds {MAX_FILE_SIZE_MB} MB limit")

        doc_filename = file.filename
        ext = file.filename.lower().rsplit(".", 1)[-1]

        if ext == "pdf":
            doc_text = _extract_pdf_text(content, file.filename)
        elif ext in ("txt", "md"):
            doc_text = _extract_txt_text(content)
        else:
            raise HTTPException(422, "Only PDF, TXT, and MD files are supported")

        if not doc_text:
            logger.warning(f"No text extracted from {file.filename}")

    # ── Persist to PostgreSQL ────────────────────────────────────────
    submission = Submission(
        id=str(uuid.uuid4()),
        question=question,
        ai_response=ai_response,
        reference_answer=reference_answer.strip() if reference_answer else None,
        document_text=doc_text,
        document_filename=doc_filename,
        status=SubmissionStatus.pending,
    )
    db.add(submission)
    await db.commit()

    logger.info(f"Submission created and committed: {submission.id}")

    # Launch evaluation in background
    background_tasks.add_task(run_evaluation, submission.id)

    return {
        "id": submission.id,
        "status": submission.status,
        "created_at": submission.created_at.isoformat(),
        "has_reference_answer": reference_answer is not None,
        "has_document": doc_filename is not None,
        "document_filename": doc_filename,
        "document_chars": len(doc_text) if doc_text else 0,
    }


# ── GET /api/submissions ─────────────────────────────────────────────
@router.get("/submissions")
async def list_submissions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    total_result = await db.execute(select(func.count()).select_from(Submission))
    total = total_result.scalar_one()

    result = await db.execute(
        select(Submission)
        .order_by(Submission.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    submissions = result.scalars().all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": s.id,
                "question": s.question[:120] + "…" if len(s.question) > 120 else s.question,
                "status": s.status,
                "has_reference": s.reference_answer is not None,
                "has_document": s.document_filename is not None,
                "document_filename": s.document_filename,
                "created_at": s.created_at.isoformat(),
            }
            for s in submissions
        ],
    }


# ── GET /api/submissions/{id} ────────────────────────────────────────
@router.get("/submissions/{submission_id}")
async def get_submission(
    submission_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Submission).where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(404, "Submission not found")

    return {
        "id": submission.id,
        "question": submission.question,
        "ai_response": submission.ai_response,
        "reference_answer": submission.reference_answer,
        "document_filename": submission.document_filename,
        "document_text_preview": (submission.document_text or "")[:500],
        "status": submission.status,
        "evaluation_results": submission.evaluation_results,
        "created_at": submission.created_at.isoformat(),
    }
