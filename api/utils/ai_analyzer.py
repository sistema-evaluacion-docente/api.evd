"""
AI comment analyzer — local inference using HuggingFace transformers pipeline.
Models are loaded once and reused across all calls (singleton pattern).
"""

import logging

from transformers import pipeline

from api.config import config

logger = logging.getLogger(__name__)

_risk_pipeline = None
_category_pipeline = None

# ponytail: fixed cutoff, expose via config if it ever needs tuning per model.
CATEGORY_SCORE_THRESHOLD = 0.5


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
            output = category_pipe(text, top_k=None)

            result["category_labels"] = [
                {"label": item["label"], "score": round(item["score"], 4)}
                for item in output
                if item["score"] >= CATEGORY_SCORE_THRESHOLD
            ]
            result["category_model"] = config.HUGGINGFACE_CATEGORY_MODEL
        except Exception as exc:
            logger.error("Category model inference failed: %s", exc)

    return result
