"""
PRISM — Dataset Loader
Loads TruthfulQA and SQuAD from Hugging Face and returns
a flat list of (text, metadata) tuples ready for cleaning.
"""
import logging
from typing import List, Tuple, Dict, Any

logger = logging.getLogger(__name__)


def _load_truthfulqa() -> List[Tuple[str, Dict[str, Any]]]:
    """
    Load TruthfulQA (generation config).
    We ingest ONLY the correct answers as trusted reference passages.
    Each row yields: best_answer + correct_answers (deduplicated).
    """
    from datasets import load_dataset

    logger.info("Loading TruthfulQA ...")
    ds = load_dataset("truthfulqa/truthful_qa", "generation", split="validation")

    records: List[Tuple[str, Dict[str, Any]]] = []
    for row in ds:
        question = row.get("question", "").strip()
        # Best answer
        best = row.get("best_answer", "").strip()
        if best:
            text = f"Q: {question}\nA: {best}"
            records.append((text, {"source": "truthfulqa", "dataset": "truthfulqa", "type": "best_answer", "question": question}))
        # Additional correct answers
        for ans in row.get("correct_answers", []):
            ans = ans.strip()
            if ans and ans != best:
                text = f"Q: {question}\nA: {ans}"
                records.append((text, {"source": "truthfulqa", "dataset": "truthfulqa", "type": "correct_answer", "question": question}))

    logger.info(f"TruthfulQA: loaded {len(records)} passages")
    return records


def _load_squad() -> List[Tuple[str, Dict[str, Any]]]:
    """
    Load SQuAD v1.1 (validation split).
    We ingest the context passages (deduplicated) — limited to 1,000 unique contexts for speed.
    """
    from datasets import load_dataset

    logger.info("Loading SQuAD (validation split, capped) ...")
    ds = load_dataset("rajpurkar/squad", split="validation")

    seen_contexts: set = set()
    records: List[Tuple[str, Dict[str, Any]]] = []
    for row in ds:
        if len(records) >= 1000:
            break
        context = row.get("context", "").strip()
        title = row.get("title", "unknown")
        if context and context not in seen_contexts:
            seen_contexts.add(context)
            records.append((
                context,
                {"source": "squad", "dataset": "squad", "type": "context", "title": title}
            ))

    logger.info(f"SQuAD: loaded {len(records)} unique context passages")
    return records


def load_sources(sources: List[str]) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Load one or more datasets and concatenate.
    `sources` can contain: 'truthfulqa', 'squad'
    """
    all_records: List[Tuple[str, Dict[str, Any]]] = []
    if "truthfulqa" in sources:
        all_records.extend(_load_truthfulqa())
    if "squad" in sources:
        all_records.extend(_load_squad())
    logger.info(f"Total raw records loaded: {len(all_records)}")
    return all_records
