"""Tests for the improvement-action suggestion catalogue.

The catalogue is deterministic and keyed by the dimensions and question codes
of ``api/utils/dimensions.py``. What is worth asserting is that it stays in step
with that source of truth and that it never hands a director an empty list —
the public signature promises a suggestion for anything it is asked about.
"""

import pytest

from api.utils.dimensions import DIMENSION_MAP, QUESTION_TEXT
from api.utils.improvement_suggestions import (
    DIMENSION_OVERALL_LABEL,
    DIMENSION_SUGGESTIONS,
    GENERIC_SUGGESTIONS,
    OVERALL_LABEL,
    QUESTION_SUGGESTIONS,
    build_indicator_catalog,
    suggest_actions,
)


class TestCatalogueMatchesTheDimensions:
    """``dimensions.py`` is the single source of truth; this must follow it."""

    def test_every_dimension_has_its_own_suggestions(self):
        """Test a dimension added to the form does not fall back to generic.

        The generic list says nothing about the dimension the director picked,
        so a missing key here is a silently worse suggestion, not an error.
        """

        assert set(DIMENSION_SUGGESTIONS) == set(DIMENSION_MAP)

    def test_every_question_of_the_form_has_its_own_suggestions(self):
        """Test the 22 questions are all covered by name."""

        codes = {code for codes in DIMENSION_MAP.values() for code in codes}

        assert set(QUESTION_SUGGESTIONS) == codes

    def test_no_suggestion_list_is_empty(self):
        """Test every entry actually carries actions."""

        for actions in (*DIMENSION_SUGGESTIONS.values(), *QUESTION_SUGGESTIONS.values()):
            assert actions

        assert GENERIC_SUGGESTIONS


class TestSuggestActions:
    """The public entry point, one branch per target type."""

    def test_a_dimension_gets_its_own_actions(self):
        """Test a known dimension resolves to its list."""

        result = suggest_actions("DIMENSION", "Procesos de Evaluación")

        assert result == DIMENSION_SUGGESTIONS["Procesos de Evaluación"]

    def test_an_unknown_dimension_falls_back_to_generic(self):
        """Test a renamed dimension still answers something usable."""

        assert suggest_actions("DIMENSION", "Inventada") == GENERIC_SUGGESTIONS

    def test_a_question_gets_its_own_actions(self):
        """Test a known question code resolves to its list."""

        assert suggest_actions("QUESTION", "017") == QUESTION_SUGGESTIONS["017"]

    def test_an_unknown_question_falls_back_to_its_dimension(self):
        """Test an unlisted code still answers within the right dimension.

        Falling straight to the generic list would lose the one thing known
        about the question — which dimension it belongs to.
        """

        original = QUESTION_SUGGESTIONS.pop("017")
        try:
            assert suggest_actions("QUESTION", "017") == DIMENSION_SUGGESTIONS[
                "Procesos de Evaluación"
            ]
        finally:
            QUESTION_SUGGESTIONS["017"] = original

    def test_a_code_outside_the_form_falls_back_to_generic(self):
        """Test a code belonging to no dimension answers generically."""

        assert suggest_actions("QUESTION", "999") == GENERIC_SUGGESTIONS

    @pytest.mark.parametrize(
        "target_type", ["OVERALL_AVERAGE", "QUALITATIVE", "PEDAGOGICAL_CATEGORY"]
    )
    def test_targets_without_a_catalogue_answer_generically(self, target_type):
        """Test the qualitative targets get the generic list, not nothing."""

        assert suggest_actions(target_type) == GENERIC_SUGGESTIONS

    def test_a_dimension_without_a_ref_answers_generically(self):
        """Test a target type with no ref cannot look anything up."""

        assert suggest_actions("DIMENSION") == GENERIC_SUGGESTIONS

    def test_never_answers_an_empty_list(self):
        """Test the promise the docstring makes holds for the whole form."""

        assert suggest_actions("OVERALL_AVERAGE")
        for dimension, codes in DIMENSION_MAP.items():
            assert suggest_actions("DIMENSION", dimension)
            for code in codes:
                assert suggest_actions("QUESTION", code)


class TestBuildIndicatorCatalog:
    """What the creation page shows a director to pick a compromiso from."""

    @pytest.fixture
    def catalog(self):
        return build_indicator_catalog()

    def test_the_overall_average_is_offered_on_its_own(self, catalog):
        """Test a plan can commit to the teacher's overall score."""

        assert catalog["overall"] == {
            "target_type": "OVERALL_AVERAGE",
            "target_ref": None,
            "label": OVERALL_LABEL,
            "suggestions": GENERIC_SUGGESTIONS,
        }

    def test_every_dimension_of_the_form_is_offered(self, catalog):
        """Test the four dimensions are all selectable."""

        offered = [entry["dimension"] for entry in catalog["dimensions"]]

        assert offered == list(DIMENSION_MAP)

    def test_a_dimension_carries_its_own_questions(self, catalog):
        """Test a director may commit to the dimension or to one question."""

        entry = next(
            e for e in catalog["dimensions"] if e["dimension"] == "Procesos de Evaluación"
        )

        assert entry["target_type"] == "DIMENSION"
        assert entry["target_ref"] == "Procesos de Evaluación"
        assert entry["label"] == DIMENSION_OVERALL_LABEL
        assert [q["code"] for q in entry["questions"]] == DIMENSION_MAP[
            "Procesos de Evaluación"
        ]

    def test_every_question_carries_the_text_it_is_printed_with(self, catalog):
        """Test the form's wording travels with the code.

        The acta prints the question, not its number, so a code without text
        would reach the signed document as a bare "017".
        """

        for entry in catalog["dimensions"]:
            for question in entry["questions"]:
                assert question["target_type"] == "QUESTION"
                assert question["text"] == QUESTION_TEXT[question["code"]]
                assert question["text"] != question["code"]
                assert question["suggestions"]
