"""Tests for the institutional_code validation shared by the teacher schemas."""

import pytest
from pydantic import ValidationError

from api.schemas.teacher import TeacherCreate, TeacherCreateWithUser, TeacherUpdate


def test_teacher_create_rejects_a_non_numeric_code():
    with pytest.raises(ValidationError):
        TeacherCreate(institutional_code="abc12")


def test_teacher_create_with_user_rejects_a_non_numeric_code():
    with pytest.raises(ValidationError):
        TeacherCreateWithUser(
            email="ana@ufps.edu.co", name="Ana", institutional_code="abc12"
        )


def test_teacher_update_rejects_a_non_numeric_code():
    with pytest.raises(ValidationError):
        TeacherUpdate(institutional_code="abc12")
