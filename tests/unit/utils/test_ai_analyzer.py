"""
Tests for api.utils.ai_analyzer.

Covers analyze_comment: the shape of the result dict, the category
confidence threshold, and the model-id attribution that lets a stored
classification be traced back to the model that produced it.
"""

from unittest.mock import MagicMock, patch

import pytest

from api.utils.ai_analyzer import CATEGORY_SCORE_THRESHOLD, MAX_LENGTH, analyze_comment

RISK_MODEL = "org/risk-model-v1"
CATEGORY_MODEL = "org/category-model-v1"


@pytest.fixture(autouse=True)
def stub_config():
    """Pin the configured model ids so assertions don't depend on the env."""

    with patch("api.utils.ai_analyzer.config") as mock_config:
        mock_config.HUGGINGFACE_RISK_MODEL = RISK_MODEL
        mock_config.HUGGINGFACE_CATEGORY_MODEL = CATEGORY_MODEL
        yield mock_config


@pytest.fixture(autouse=True)
def stub_category_tokenizer():
    """No tokenizer by default: falls back to single-chunk (see ai_analyzer's
    ``_chunk_for_category_model``), same as a comment short enough not to
    need chunking. Fetching a real one would hit the network for a model id
    that doesn't exist. Tests that care about chunking override this."""

    with patch("api.utils.ai_analyzer._get_category_tokenizer", return_value=None):
        yield


def _risk_pipe(label="ALTO", score=0.98123):
    return MagicMock(return_value=[{"label": label, "score": score}])


def _category_pipe(items):
    return MagicMock(return_value=items)


class TestAnalyzeComment:
    """Test suite for analyze_comment."""

    @patch("api.utils.ai_analyzer._get_category_pipeline")
    @patch("api.utils.ai_analyzer._get_risk_pipeline")
    def test_analyze_comment_with_both_models_reports_each_model_id(
        self, mock_get_risk, mock_get_category
    ):
        """Test analyze_comment records which model produced each classification."""

        mock_get_risk.return_value = _risk_pipe()
        mock_get_category.return_value = _category_pipe(
            [{"label": "CLARIDAD", "score": 0.9}]
        )

        result = analyze_comment("El docente no explica con claridad")

        assert result["risk_label"] == "ALTO"
        assert result["risk_score"] == 0.9812
        assert result["risk_model"] == RISK_MODEL
        assert result["category_labels"] == [{"label": "CLARIDAD", "score": 0.9}]
        assert result["category_model"] == CATEGORY_MODEL

    @patch("api.utils.ai_analyzer._get_category_pipeline")
    @patch("api.utils.ai_analyzer._get_risk_pipeline")
    def test_analyze_comment_without_pipelines_reports_no_models(
        self, mock_get_risk, mock_get_category
    ):
        """Test analyze_comment leaves both model ids as None when no model loaded."""

        mock_get_risk.return_value = None
        mock_get_category.return_value = None

        result = analyze_comment("Un comentario cualquiera")

        assert result == {
            "risk_label": None,
            "risk_score": None,
            "risk_model": None,
            "category_labels": [],
            "category_model": None,
        }

    @patch("api.utils.ai_analyzer._get_category_pipeline")
    @patch("api.utils.ai_analyzer._get_risk_pipeline")
    def test_analyze_comment_when_risk_inference_fails_reports_no_risk_model(
        self, mock_get_risk, mock_get_category
    ):
        """Test a failed risk inference attributes no model to the risk half."""

        mock_get_risk.return_value = MagicMock(side_effect=RuntimeError("boom"))
        mock_get_category.return_value = _category_pipe(
            [{"label": "CLARIDAD", "score": 0.9}]
        )

        result = analyze_comment("El docente no explica con claridad")

        assert result["risk_label"] is None
        assert result["risk_model"] is None
        # The category half is independent and still reports its model.
        assert result["category_model"] == CATEGORY_MODEL

    @patch("api.utils.ai_analyzer._get_category_pipeline")
    @patch("api.utils.ai_analyzer._get_risk_pipeline")
    def test_analyze_comment_when_category_inference_fails_reports_no_category_model(
        self, mock_get_risk, mock_get_category
    ):
        """Test a failed category inference attributes no model to the category half."""

        mock_get_risk.return_value = _risk_pipe()
        mock_get_category.return_value = MagicMock(side_effect=RuntimeError("boom"))

        result = analyze_comment("El docente no explica con claridad")

        assert result["category_labels"] == []
        assert result["category_model"] is None
        assert result["risk_model"] == RISK_MODEL

    @patch("api.utils.ai_analyzer._get_category_pipeline")
    @patch("api.utils.ai_analyzer._get_risk_pipeline")
    def test_analyze_comment_drops_categories_below_threshold(
        self, mock_get_risk, mock_get_category
    ):
        """Test only categories clearing CATEGORY_SCORE_THRESHOLD are returned."""

        mock_get_risk.return_value = _risk_pipe()
        mock_get_category.return_value = _category_pipe(
            [
                {"label": "CLARIDAD", "score": CATEGORY_SCORE_THRESHOLD},
                {"label": "PUNTUALIDAD", "score": CATEGORY_SCORE_THRESHOLD - 0.01},
            ]
        )

        result = analyze_comment("El docente no explica con claridad")

        assert [item["label"] for item in result["category_labels"]] == ["CLARIDAD"]
        # The model still ran, so it is still the source of the (filtered) result.
        assert result["category_model"] == CATEGORY_MODEL

    @patch("api.utils.ai_analyzer._get_category_pipeline")
    @patch("api.utils.ai_analyzer._get_risk_pipeline")
    def test_analyze_comment_calls_risk_model_unchanged(
        self, mock_get_risk, mock_get_category
    ):
        """DistilBETO (risk) is left exactly as it was — no truncation, no
        max_length — since it already works correctly without chunking (it
        has 512 position embeddings) and the category fix must not touch it."""

        mock_risk_pipe = _risk_pipe()
        mock_get_risk.return_value = mock_risk_pipe
        mock_get_category.return_value = None

        analyze_comment("El docente no explica con claridad")

        mock_risk_pipe.assert_called_once_with("El docente no explica con claridad")

    @patch("api.utils.ai_analyzer._get_category_pipeline")
    @patch("api.utils.ai_analyzer._get_risk_pipeline")
    def test_analyze_comment_short_text_calls_category_model_once(
        self, mock_get_risk, mock_get_category
    ):
        """A comment short enough for one window (the no-tokenizer fallback,
        via stub_category_tokenizer) is still passed with truncation/max_length
        as a safety net, and the model runs exactly once."""

        mock_get_risk.return_value = _risk_pipe()
        mock_category_pipe = _category_pipe([{"label": "CLARIDAD", "score": 0.9}])
        mock_get_category.return_value = mock_category_pipe

        analyze_comment("El docente no explica con claridad")

        mock_category_pipe.assert_called_once_with(
            "El docente no explica con claridad",
            truncation=True,
            max_length=MAX_LENGTH,
            top_k=None,
        )


class _FakeCategoryTokenizer:
    """Splits any text into a fixed number of made-up overlapping windows —
    enough to exercise the chunking path without a real model."""

    def __init__(self, num_chunks: int):
        self.num_chunks = num_chunks

    def __call__(self, text, **kwargs):
        return {"input_ids": [[i] for i in range(self.num_chunks)]}

    def decode(self, ids, skip_special_tokens=True):
        return f"chunk-{ids[0]}"


class TestAnalyzeCommentCategoryChunking:
    """RoBERTuito (category) has only 128 position-embedding rows: a comment
    that tokenizes past that raises IndexError instead of degrading, so long
    comments are split into overlapping windows and the scores per label are
    averaged across them (see _chunk_for_category_model / _aggregate_category_scores)."""

    @patch("api.utils.ai_analyzer._get_category_tokenizer")
    @patch("api.utils.ai_analyzer._get_category_pipeline")
    @patch("api.utils.ai_analyzer._get_risk_pipeline")
    def test_long_comment_is_chunked_and_scores_averaged(
        self, mock_get_risk, mock_get_category, mock_get_tokenizer
    ):
        mock_get_risk.return_value = None
        mock_get_tokenizer.return_value = _FakeCategoryTokenizer(num_chunks=2)

        per_chunk_results = [
            [{"label": "CLARIDAD", "score": 0.9}, {"label": "PUNTUALIDAD", "score": 0.2}],
            [{"label": "CLARIDAD", "score": 0.7}, {"label": "PUNTUALIDAD", "score": 0.5}],
        ]
        mock_category_pipe = MagicMock(return_value=per_chunk_results)
        mock_get_category.return_value = mock_category_pipe

        result = analyze_comment("un comentario muy largo " * 50)

        # One batched call carrying every window, never a loop calling the
        # pipeline once per chunk.
        mock_category_pipe.assert_called_once_with(
            ["chunk-0", "chunk-1"],
            truncation=True,
            max_length=MAX_LENGTH,
            top_k=None,
        )
        # CLARIDAD: (0.9 + 0.7) / 2 = 0.8 — clears the threshold.
        # PUNTUALIDAD: (0.2 + 0.5) / 2 = 0.35 — does not.
        assert result["category_labels"] == [{"label": "CLARIDAD", "score": 0.8}]
        assert result["category_model"] == CATEGORY_MODEL

    @patch("api.utils.ai_analyzer._get_category_tokenizer")
    @patch("api.utils.ai_analyzer._get_category_pipeline")
    @patch("api.utils.ai_analyzer._get_risk_pipeline")
    def test_single_window_comment_skips_aggregation(
        self, mock_get_risk, mock_get_category, mock_get_tokenizer
    ):
        """A comment that tokenizes to exactly one window is passed through
        directly (as a string, not a one-item list) — no averaging needed."""

        mock_get_risk.return_value = None
        mock_get_tokenizer.return_value = _FakeCategoryTokenizer(num_chunks=1)
        mock_category_pipe = _category_pipe([{"label": "CLARIDAD", "score": 0.9}])
        mock_get_category.return_value = mock_category_pipe

        result = analyze_comment("comentario corto")

        mock_category_pipe.assert_called_once_with(
            "chunk-0", truncation=True, max_length=MAX_LENGTH, top_k=None
        )
        assert result["category_labels"] == [{"label": "CLARIDAD", "score": 0.9}]
