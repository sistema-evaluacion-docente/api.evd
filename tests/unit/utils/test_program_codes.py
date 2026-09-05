"""Tests for program_code_of — extracting a course code's COD_CARRERA prefix."""

import pytest

from api.utils.program_codes import program_code_of


@pytest.mark.parametrize(
    "course_code,expected",
    [
        ("1155304", "115"),
        ("1160103", "116"),
        (" 1210108 ", "121"),
        (None, None),
        ("", None),
        ("AB", None),
        ("AB1234", None),
    ],
)
def test_program_code_of(course_code, expected):
    assert program_code_of(course_code) == expected
