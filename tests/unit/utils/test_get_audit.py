"""Tests for get_audit — the element-id dispatcher audit logs use to
resolve "table id" strings back into a serialized record."""

from unittest.mock import MagicMock, patch

import pytest

from api.utils.get_audit import get_audit

pytestmark = pytest.mark.asyncio


async def test_user_by_numeric_id(mock_db):
    """Test a numeric id looks the user up by id."""

    row = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = row

    with patch("api.utils.get_audit.user_to_dict", return_value={"id": 1}) as serialize:
        result = await get_audit("User 1", mock_db)

    assert result == {"id": 1}
    serialize.assert_called_once_with(row)


async def test_user_by_uid_falls_back_when_id_is_not_numeric(mock_db):
    """Test a non-numeric id is treated as a Firebase uid instead."""

    row = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = row

    with patch("api.utils.get_audit.user_to_dict", return_value={"uid": "abc"}):
        result = await get_audit("User abc-uid", mock_db)

    assert result == {"uid": "abc"}


async def test_department(mock_db):
    """Test a Department element is resolved through its serializer."""

    with patch(
        "api.utils.get_audit.department_to_dict", return_value={"id": 1}
    ) as serialize:
        result = await get_audit("Department 1", mock_db)

    assert result == {"id": 1}
    serialize.assert_called_once()


async def test_faculty(mock_db):
    """Test a Faculty element is resolved through its serializer."""

    with patch("api.utils.get_audit.faculty_to_dict", return_value={"id": 1}):
        result = await get_audit("Faculty 1", mock_db)

    assert result == {"id": 1}


async def test_academic_period(mock_db):
    """Test an AcademicPeriod element is resolved through its serializer."""

    with patch(
        "api.utils.get_audit.academic_period_to_dict", return_value={"id": 1}
    ):
        result = await get_audit("AcademicPeriod 1", mock_db)

    assert result == {"id": 1}


async def test_teacher(mock_db):
    """Test a Teacher element is resolved through its serializer."""

    with patch("api.utils.get_audit.teacher_to_dict", return_value={"id": 1}):
        result = await get_audit("Teacher 1", mock_db)

    assert result == {"id": 1}


async def test_setting(mock_db):
    """Test a Setting element is resolved through its serializer."""

    with patch("api.utils.get_audit.setting_to_dict", return_value={"id": 1}):
        result = await get_audit("Setting 1", mock_db)

    assert result == {"id": 1}


async def test_academic_group(mock_db):
    """Test an AcademicGroup element is resolved through its serializer."""

    with patch(
        "api.utils.get_audit.academic_group_to_dict", return_value={"id": 1}
    ):
        result = await get_audit("AcademicGroup 1", mock_db)

    assert result == {"id": 1}


async def test_course(mock_db):
    """Test a Course element is resolved through its serializer."""

    with patch("api.utils.get_audit.course_to_dict", return_value={"id": 1}):
        result = await get_audit("Course 1", mock_db)

    assert result == {"id": 1}


async def test_director(mock_db):
    """Test a Director element is resolved through its serializer."""

    with patch("api.utils.get_audit.director_to_dict", return_value={"id": 1}):
        result = await get_audit("Director 1", mock_db)

    assert result == {"id": 1}


async def test_unknown_table_returns_none(mock_db):
    """Test an unrecognized table name resolves to None."""

    result = await get_audit("Unknown 1", mock_db)

    assert result is None
