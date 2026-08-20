"""
Tests for api.utils.ai_analyzer.

Covers analyze_comment: the shape of the result dict, the category
confidence threshold, and the model-id attribution that lets a stored
classification be traced back to the model that produced it.
"""

from unittest.mock import MagicMock, patch

import pytest

from api.utils.ai_analyzer import CATEGORY_SCORE_THRESHOLD, analyze_comment

RISK_MODEL = "org/risk-model-v1"
CATEGORY_MODEL = "org/category-model-v1"


@pytest.fixture(autouse=True)
def stub_config():
    """Pin the configured model ids so assertions don't depend on the env."""

    with patch("api.utils.ai_analyzer.config") as mock_config:
        mock_config.HUGGINGFACE_RISK_MODEL = RISK_MODEL
        mock_config.HUGGINGFACE_CATEGORY_MODEL = CATEGORY_MODEL
        yield mock_config


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
