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


def _get_risk_pipeline():
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

    Returns the top label and confidence score for risk level and pedagogical
    category. Any field is None if the model fails or is not configured.
    """
    result = {
        "risk_label": None,
        "risk_score": None,
        "category_label": None,
        "category_score": None,
    }

    risk_pipe = _get_risk_pipeline()
    if risk_pipe:
        try:
            output = risk_pipe(text)
            result["risk_label"] = output[0]["label"]
            result["risk_score"] = round(output[0]["score"], 4)
        except Exception as exc:
            logger.error("Risk model inference failed: %s", exc)

    category_pipe = _get_category_pipeline()
    if category_pipe:
        try:
            output = category_pipe(text)
            result["category_label"] = output[0]["label"]
            result["category_score"] = round(output[0]["score"], 4)
        except Exception as exc:
            logger.error("Category model inference failed: %s", exc)

    return result
