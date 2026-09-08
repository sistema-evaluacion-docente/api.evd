"""
AI comment analyzer — local inference using HuggingFace transformers pipeline.
Models are loaded once and reused across all calls (singleton pattern).
"""

import logging

from transformers import AutoTokenizer, pipeline

from api.config import config

logger = logging.getLogger(__name__)

_risk_pipeline = None
_category_pipeline = None
_category_tokenizer = None

# ponytail: fixed cutoff, expose via config if it ever needs tuning per model.
CATEGORY_SCORE_THRESHOLD = 0.5

# The category model (RoBERTuito) has only 128 position-embedding rows —
# encoding past that raises IndexError, not just a quality drop — so long
# comments are chunked below instead of truncated: truncating would silently
# drop real content, and this model is the best performer of the ones
# evaluated. Also its max_length from training/evaluation.
# The risk model (DistilBETO) deliberately isn't touched here: it has 512
# position embeddings so it never raises, and it's left calling the pipeline
# exactly as before — no truncation, no max_length — since that's already
# working correctly in production.
MAX_LENGTH = 128
CATEGORY_CHUNK_STRIDE = 24


def _get_risk_pipeline():
    """Get the HuggingFace pipeline for risk level classification."""

    global _risk_pipeline

    if _risk_pipeline is None:
        try:
            _risk_pipeline = pipeline(
                "text-classification",
                model=config.HUGGINGFACE_RISK_MODEL,
            )
            logger.info("Risk model loaded: %s", config.HUGGINGFACE_RISK_MODEL)
        except Exception as exc:
            logger.error("Failed to load risk model: %s", exc)
    return _risk_pipeline


def _get_category_pipeline():
    """Get the HuggingFace pipeline for pedagogical category classification."""

    global _category_pipeline

    if _category_pipeline is None:
        try:
            _category_pipeline = pipeline(
                "text-classification",
                model=config.HUGGINGFACE_CATEGORY_MODEL,
            )
            logger.info("Category model loaded: %s", config.HUGGINGFACE_CATEGORY_MODEL)
        except Exception as exc:
            logger.error("Failed to load category model: %s", exc)
    return _category_pipeline


def _get_category_tokenizer():
    """Tokenizer for the category model, used only to split long comments into
    windows it can classify without raising (see ``_chunk_for_category_model``)."""

    global _category_tokenizer

    if _category_tokenizer is None:
        try:
            _category_tokenizer = AutoTokenizer.from_pretrained(
                config.HUGGINGFACE_CATEGORY_MODEL
            )
        except Exception as exc:
            logger.error("Failed to load category tokenizer: %s", exc)
    return _category_tokenizer


def _chunk_for_category_model(text: str) -> list[str]:
    """Split ``text`` into overlapping windows of at most MAX_LENGTH tokens.

    The stride keeps a 24-token overlap between windows so an idea sitting
    on a window boundary isn't split without any shared context. Falls back
    to the untouched text (still safe: the pipeline call itself also passes
    truncation=True/max_length) if the tokenizer can't be loaded.
    """

    tokenizer = _get_category_tokenizer()

    if tokenizer is None:
        return [text]

    encoded = tokenizer(
        text,
        truncation=True,
        max_length=MAX_LENGTH,
        stride=CATEGORY_CHUNK_STRIDE,
        return_overflowing_tokens=True,
        add_special_tokens=True,
    )
    chunks = [
        tokenizer.decode(ids, skip_special_tokens=True)
        for ids in encoded["input_ids"]
    ]
    return chunks or [text]


def _aggregate_category_scores(per_chunk_results: list[list[dict]]) -> list[dict]:
    """Average each label's score across chunks.

    Mean, not max: a comment's overall category is what most of it is about,
    not whichever single window happened to score highest — unlike risk,
    where a single alarming window should be enough to flag the comment (see
    the risk half of analyze_comment, which doesn't chunk in this app: the
    risk model here is DistilBETO, which doesn't need it).
    """

    scores_by_label: dict[str, list[float]] = {}

    for chunk_result in per_chunk_results:
        for item in chunk_result:
            scores_by_label.setdefault(item["label"], []).append(item["score"])

    return [
        {"label": label, "score": sum(scores) / len(scores)}
        for label, scores in scores_by_label.items()
    ]


def analyze_comment(text: str) -> dict:
    """Run both classification models on a comment text.

    Returns the top label/score for risk level, and every pedagogical
    category whose confidence clears ``CATEGORY_SCORE_THRESHOLD`` (0, 1 or
    several — a comment can touch more than one pedagogical dimension).
    Each half also reports the model id that produced it, so the stored
    classification can be traced back to a concrete model version.
    Fields are None/empty if the model fails or is not configured.
    """

    result = {
        "risk_label": None,
        "risk_score": None,
        "risk_model": None,
        "category_labels": [],
        "category_model": None,
    }

    risk_pipe = _get_risk_pipeline()

    if risk_pipe:
        try:
            output = risk_pipe(text)

            result["risk_label"] = output[0]["label"]
            result["risk_score"] = round(output[0]["score"], 4)
            result["risk_model"] = config.HUGGINGFACE_RISK_MODEL
        except Exception as exc:
            logger.error("Risk model inference failed: %s", exc)

    category_pipe = _get_category_pipeline()

    if category_pipe:
        try:
            chunks = _chunk_for_category_model(text)

            if len(chunks) == 1:
                output = category_pipe(
                    chunks[0], truncation=True, max_length=MAX_LENGTH, top_k=None
                )
            else:
                # One batched call for every window, not a loop, so the model
                # still runs once per comment instead of once per window.
                per_chunk_results = category_pipe(
                    chunks, truncation=True, max_length=MAX_LENGTH, top_k=None
                )
                output = _aggregate_category_scores(per_chunk_results)

            result["category_labels"] = [
                {"label": item["label"], "score": round(item["score"], 4)}
                for item in output
                if item["score"] >= CATEGORY_SCORE_THRESHOLD
            ]
            result["category_model"] = config.HUGGINGFACE_CATEGORY_MODEL
        except Exception as exc:
            logger.error("Category model inference failed: %s", exc)

    return result
