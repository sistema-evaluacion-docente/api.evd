"""Tests for aspect_for_target — resolving an item's official-form aspect."""

from api.utils.dimensions import aspect_for_target


def test_dimension_target_resolves_through_its_dimension_name():
    assert aspect_for_target("DIMENSION", "Desempeño Docente") == 2


def test_question_target_resolves_through_its_owning_dimension():
    # Question "007" belongs to "Desempeño Docente" (aspect 2).
    assert aspect_for_target("QUESTION", "007") == 2


def test_question_target_with_an_unknown_code_is_unassigned():
    assert aspect_for_target("QUESTION", "999") is None


def test_dimension_target_without_a_ref_is_unassigned():
    assert aspect_for_target("DIMENSION", None) is None


def test_qualitative_target_is_always_unassigned():
    assert aspect_for_target("QUALITATIVE", None) is None


def test_overall_average_target_is_always_unassigned():
    assert aspect_for_target("OVERALL_AVERAGE", None) is None
