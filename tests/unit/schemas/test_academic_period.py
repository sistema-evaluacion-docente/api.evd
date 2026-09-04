"""Tests for the date-ordering validation shared by AcademicPeriodCreate/Update."""

from datetime import date

import pytest
from pydantic import ValidationError

from api.schemas.academic_period import AcademicPeriodCreate, AcademicPeriodUpdate


class TestAcademicPeriodCreateDates:
    def test_accepts_a_well_ordered_period(self):
        AcademicPeriodCreate(
            name="2026-1",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
            evaluation_end_date=date(2026, 6, 1),
            final_evaluation_date=date(2026, 5, 15),
        )

    def test_rejects_an_end_date_before_the_start_date(self):
        with pytest.raises(ValidationError):
            AcademicPeriodCreate(
                name="2026-1",
                start_date=date(2026, 6, 1),
                end_date=date(2026, 1, 1),
            )

    def test_rejects_an_evaluation_end_date_after_the_end_date(self):
        with pytest.raises(ValidationError):
            AcademicPeriodCreate(
                name="2026-1",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 6, 1),
                evaluation_end_date=date(2026, 7, 1),
            )

    def test_rejects_a_final_evaluation_date_after_the_evaluation_end_date(self):
        with pytest.raises(ValidationError):
            AcademicPeriodCreate(
                name="2026-1",
                evaluation_end_date=date(2026, 6, 1),
                final_evaluation_date=date(2026, 7, 1),
            )


class TestAcademicPeriodUpdateDates:
    def test_accepts_a_well_ordered_period(self):
        AcademicPeriodUpdate(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )

    def test_rejects_an_end_date_before_the_start_date(self):
        with pytest.raises(ValidationError):
            AcademicPeriodUpdate(
                start_date=date(2026, 6, 1),
                end_date=date(2026, 1, 1),
            )

    def test_rejects_an_evaluation_end_date_after_the_end_date(self):
        with pytest.raises(ValidationError):
            AcademicPeriodUpdate(
                end_date=date(2026, 6, 1),
                evaluation_end_date=date(2026, 7, 1),
            )

    def test_rejects_a_final_evaluation_date_after_the_evaluation_end_date(self):
        with pytest.raises(ValidationError):
            AcademicPeriodUpdate(
                evaluation_end_date=date(2026, 6, 1),
                final_evaluation_date=date(2026, 7, 1),
            )
