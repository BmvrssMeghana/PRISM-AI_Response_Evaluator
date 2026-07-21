"""
PRISM — Evaluation Orchestrator
Coordinates the full RAG-grounded multi-agent judging pipeline.
Runs as a non-blocking background task after user submission.
"""
import asyncio
import logging
from typing import Optional
from sqlalchemy import select

from core.database import AsyncSessionFactory, Submission, SubmissionStatus
from retrieval.retriever import retrieve
from services.agents import (
    extract_claims,
    evaluate_relevance,
    evaluate_accuracy,
    evaluate_hallucination,
    evaluate_confidence,
    evaluate_safety,
)

logger = logging.getLogger(__name__)

async def run_evaluation(submission_id: str) -> None:
    """
    Load submission from database, retrieve reference material, run the agents,
    and save the structured evaluation report.
    """
    logger.info(f"Starting evaluation task for submission: {submission_id}")

    # 1. Fetch submission from database
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Submission).where(Submission.id == submission_id)
        )
        submission = result.scalar_one_or_none()
        if not submission:
            logger.error(f"Submission {submission_id} not found in database.")
            return

        # Prepare input variables
        question = submission.question
        ai_response = submission.ai_response
        ref_answer = submission.reference_answer

    try:
        # 2. Semantic retrieval from reference knowledge base (ChromaDB)
        logger.info(f"[{submission_id}] Retrieving evidence chunks...")
        # If the user uploaded a custom document, retrieve could ideally combine it,
        # but for Milestone 2 we fetch the top-5 chunks from the vector database.
        retrieved_passages = []
        try:
            retrieved_passages = retrieve(question, k=5)
        except Exception as e:
            logger.error(f"[{submission_id}] Vector store retrieval failed: {e}. Continuing with empty context.")

        # 3. Extract claims from response
        logger.info(f"[{submission_id}] Extracting claims...")
        claims = await extract_claims(ai_response)
        logger.info(f"[{submission_id}] Extracted {len(claims)} atomic claims.")

        # 4. Run first batch of agents in parallel
        logger.info(f"[{submission_id}] Running Relevance, Accuracy, Hallucination, and Safety agents...")
        
        # Parallel gather
        relevance_task = evaluate_relevance(question, ai_response)
        accuracy_task = evaluate_accuracy(claims, retrieved_passages, ref_answer)
        hallucination_task = evaluate_hallucination(claims, retrieved_passages)
        safety_task = evaluate_safety(question, ai_response)

        relevance_res, accuracy_res, hallucination_res, safety_res = await asyncio.gather(
            relevance_task,
            accuracy_task,
            hallucination_task,
            safety_task,
        )

        # 5. Run Confidence Calibration Agent (depends on Accuracy & Hallucination results)
        logger.info(f"[{submission_id}] Running Confidence Calibration agent...")
        verifications = accuracy_res.get("verifications", [])
        unsupported = hallucination_res.get("unsupported_claims", [])
        confidence_res = await evaluate_confidence(ai_response, verifications, unsupported)

        # 6. Assemble the structured report
        report = {
            "claims": claims,
            "retrieved_passages": retrieved_passages,
            "relevance": {
                "score": float(relevance_res.get("score", 0.0)),
                "justification": relevance_res.get("justification", "N/A"),
            },
            "accuracy": {
                "score": float(accuracy_res.get("score", 0.0)),
                "justification": accuracy_res.get("justification", "N/A"),
                "verifications": verifications,
            },
            "hallucination": {
                "score": float(hallucination_res.get("score", 0.0)),
                "justification": hallucination_res.get("justification", "N/A"),
                "unsupported_claims": unsupported,
            },
            "confidence": {
                "score": float(confidence_res.get("score", 0.0)),
                "justification": confidence_res.get("justification", "N/A"),
            },
            "safety": {
                "vetoed": bool(safety_res.get("vetoed", False)),
                "reason": safety_res.get("reason", "Clean"),
            }
        }

        # 7. Write results back to PostgreSQL
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(Submission).where(Submission.id == submission_id)
            )
            sub = result.scalar_one_or_none()
            if sub:
                sub.evaluation_results = report
                sub.status = SubmissionStatus.evaluated
                await session.commit()
                logger.info(f"[{submission_id}] Evaluation complete. Results written successfully. [OK]")
            else:
                logger.error(f"[{submission_id}] Could not write results. Row was deleted.")

    except Exception as e:
        logger.error(f"[{submission_id}] Orchestration failed: {e}", exc_info=True)
        # Mark submission as failed
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(Submission).where(Submission.id == submission_id)
            )
            sub = result.scalar_one_or_none()
            if sub:
                sub.status = SubmissionStatus.failed
                await session.commit()
