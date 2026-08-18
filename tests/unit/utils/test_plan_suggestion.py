"""
Tests for api.utils.plan_suggestion — the rule that decides when the system
suggests an improvement plan for a teacher.

The rule is shared by the candidates endpoint and by the notification raised
after an evaluation is analysed, so it is tested on its own.
"""

from api.utils.plan_suggestion import is_plan_suggested, suggestion_reasons


def _candidate(**overrides) -> dict:
    """A teacher with nothing wrong, to be spoiled one field at a time."""

    candidate = {
        "teacher_id": 7,
        "name": "Ada Lovelace",
        "overall_average": 4.4,
        "below_threshold": False,
        "has_plan": False,
        "high_risk_comment_count": 0,
        "weak_dimensions": [],
        "weak_questions": [],
    }
    candidate.update(overrides)

    return candidate


class TestIsPlanSuggested:
    def test_healthy_teacher_is_not_suggested(self):
        assert is_plan_suggested(_candidate()) is False

    def test_overall_average_under_the_threshold(self):
        assert is_plan_suggested(_candidate(below_threshold=True)) is True

    def test_a_single_weak_question_with_a_healthy_average(self):
        candidate = _candidate(weak_questions=[{"code": "011"}])

        assert is_plan_suggested(candidate) is True

    def test_a_single_weak_dimension(self):
        candidate = _candidate(weak_dimensions=[{"dimension": "Planeación"}])

        assert is_plan_suggested(candidate) is True

    def test_a_high_risk_comment_on_its_own(self):
        assert is_plan_suggested(_candidate(high_risk_comment_count=1)) is True

    def test_missing_fields_do_not_raise(self):
        assert is_plan_suggested({}) is False


class TestSuggestionReasons:
    def test_lists_every_reason_that_fired(self):
        candidate = _candidate(
            below_threshold=True,
            weak_dimensions=[{"dimension": "Planeación"}],
            weak_questions=[{"code": "011"}],
            high_risk_comment_count=2,
        )

        assert suggestion_reasons(candidate) == [
            "promedio general bajo el umbral",
            "2 indicadores bajo el umbral",
            "2 comentarios de riesgo alto",
        ]

    def test_keeps_the_singular_when_only_one_fired(self):
        candidate = _candidate(weak_questions=[{"code": "011"}])

        assert suggestion_reasons(candidate) == ["1 indicador bajo el umbral"]

    def test_empty_when_nothing_fired(self):
        assert suggestion_reasons(_candidate()) == []
