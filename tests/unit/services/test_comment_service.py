"""
Tests for CommentService layer.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.exceptions import PermissionDeniedError, ResourceNotFoundError
from api.schemas.comment import CommentFilters, CommentUpdate
from api.services.comment_service import CommentService


class TestCommentService:
    """Test suite for CommentService."""

    @pytest.fixture
    def mock_comments_repo(self):
        """Mock CommentsRepository."""

        repo = MagicMock()
        repo.db = MagicMock()
        return repo

    @pytest.fixture
    def mock_academic_periods_repo(self):
        """Mock AcademicPeriodsRepository."""

        return MagicMock()

    @pytest.fixture
    def mock_risk_levels_repo(self):
        """Mock RiskLevelsRepository."""

        repo = MagicMock()
        repo.get_by_id = AsyncMock()
        return repo

    @pytest.fixture
    def mock_pedagogical_categories_repo(self):
        """Mock PedagogicalCategoriesRepository."""

        repo = MagicMock()
        repo.get_by_id = AsyncMock()
        return repo

    @pytest.fixture
    def mock_audit_service(self):
        """Mock AuditService."""

        service = MagicMock()
        service.log = AsyncMock()
        return service

    @pytest.fixture
    def mock_notification_service(self):
        """Mock NotificationService."""

        service = MagicMock()
        service.create = AsyncMock()
        return service

    @pytest.fixture
    def service(
        self,
        mock_comments_repo,
        mock_academic_periods_repo,
        mock_risk_levels_repo,
        mock_pedagogical_categories_repo,
        mock_audit_service,
        mock_notification_service,
    ):
        """Create service instance with mocked dependencies."""

        return CommentService(
            mock_comments_repo,
            mock_academic_periods_repo,
            mock_risk_levels_repo,
            mock_pedagogical_categories_repo,
            mock_audit_service,
            mock_notification_service,
        )

    @pytest.mark.asyncio
    async def test_get_all_returns_paginated_comments(
        self, service, mock_comments_repo
    ):
        """Test get_all returns paginated comments."""

        items = [{"id": 1}, {"id": 2}]
        mock_comments_repo.search.return_value = (items, 2)

        filters = CommentFilters()
        pagination = PaginationParams(page=1, limit=10)

        result = await service.get_all(filters, pagination)

        assert result["items"] == items
        assert result["total"] == 2
        assert result["page"] == 1
        assert result["limit"] == 10
        mock_comments_repo.search.assert_called_once_with(filters, pagination, None)

    @pytest.mark.asyncio
    async def test_get_by_id_returns_comment(self, service, mock_comments_repo):
        """Test get_by_id returns comment dict."""

        mock_comments_repo.get_by_id_enriched.return_value = {
            "id": 1,
            "original_text": "Test comment",
        }

        result = await service.get_by_id(1)

        assert result == {"id": 1, "original_text": "Test comment"}
        mock_comments_repo.get_by_id_enriched.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_when_not_found(
        self, service, mock_comments_repo
    ):
        """Test get_by_id returns None when comment not found."""

        mock_comments_repo.get_by_id_enriched.return_value = None

        result = await service.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_count_by_department_and_period_returns_counts(
        self, service, mock_comments_repo, mock_academic_periods_repo
    ):
        """Test count_by_department_and_period returns counts."""

        mock_period = MagicMock()
        mock_period.code = "2024-1"
        mock_academic_periods_repo.get.return_value = mock_period
        mock_academic_periods_repo.get_previous_period_code.return_value = "2023-2"

        mock_prev_period = MagicMock()
        mock_prev_period.id = 2
        mock_academic_periods_repo.get_by_code.return_value = mock_prev_period

        mock_comments_repo.count_by_department_and_period.return_value = {
            "current_count": 10,
            "previous_count": 8,
        }

        result = await service.count_by_department_and_period(
            department_id=1,
            academic_period_id=1,
            risk_level=None,
            pedagogical_category_id=None,
            teacher_id=None,
        )

        assert result["current_count"] == 10
        assert result["previous_count"] == 8
        mock_comments_repo.count_by_department_and_period.assert_called_once_with(
            1, 1, 2, None, None, None
        )

    @pytest.mark.asyncio
    async def test_count_by_department_and_period_without_previous(
        self, service, mock_comments_repo, mock_academic_periods_repo
    ):
        """Test count_by_department_and_period when no previous period exists."""

        mock_period = MagicMock()
        mock_period.code = "2024-1"
        mock_academic_periods_repo.get.return_value = mock_period
        mock_academic_periods_repo.get_previous_period_code.return_value = None

        mock_comments_repo.count_by_department_and_period.return_value = {
            "current_count": 5,
            "previous_count": None,
        }

        result = await service.count_by_department_and_period(
            department_id=1,
            academic_period_id=1,
        )

        assert result["current_count"] == 5
        assert result["previous_count"] is None
        mock_comments_repo.count_by_department_and_period.assert_called_once_with(
            1, 1, None, None, None, None
        )

    @pytest.mark.asyncio
    async def test_update_classification_returns_none_when_comment_not_found(
        self, service, mock_comments_repo
    ):
        """Test update_classification returns None when the comment has no department."""

        mock_comments_repo.get_department_id.return_value = None

        result = await service.update_classification(
            999, CommentUpdate(risk_level=2), {"id": 1, "department_id": 1}
        )

        assert result is None
        mock_comments_repo.update_classification.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_classification_raises_when_department_mismatch(
        self, service, mock_comments_repo
    ):
        """Test update_classification raises PermissionDeniedError for another department."""

        mock_comments_repo.get_department_id.return_value = 2

        with pytest.raises(PermissionDeniedError):
            await service.update_classification(
                1, CommentUpdate(risk_level=2), {"id": 1, "department_id": 1}
            )

        mock_comments_repo.update_classification.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_classification_raises_when_risk_level_not_found(
        self, service, mock_comments_repo, mock_risk_levels_repo
    ):
        """Test update_classification raises ResourceNotFoundError for an invalid risk_level."""

        mock_comments_repo.get_department_id.return_value = 1
        mock_risk_levels_repo.get_by_id.return_value = None

        with pytest.raises(ResourceNotFoundError):
            await service.update_classification(
                1, CommentUpdate(risk_level=999), {"id": 1, "department_id": 1}
            )

        mock_comments_repo.update_classification.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_classification_raises_when_category_not_found(
        self, service, mock_comments_repo, mock_pedagogical_categories_repo
    ):
        """Test update_classification raises ResourceNotFoundError for an invalid category."""

        mock_comments_repo.get_department_id.return_value = 1
        mock_pedagogical_categories_repo.get_by_id.return_value = None

        with pytest.raises(ResourceNotFoundError):
            await service.update_classification(
                1,
                CommentUpdate(pedagogical_category_ids=[999]),
                {"id": 1, "department_id": 1},
            )

        mock_comments_repo.update_classification.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_classification_updates_and_logs_audit(
        self,
        service,
        mock_comments_repo,
        mock_risk_levels_repo,
        mock_audit_service,
    ):
        """Test update_classification updates the comment and logs an audit entry."""

        mock_comments_repo.get_department_id.return_value = 1
        mock_risk_levels_repo.get_by_id.return_value = {"id": 2, "name": "Alto"}
        mock_comments_repo.update_classification.return_value = MagicMock()
        mock_comments_repo.get_by_id_enriched.return_value = {
            "id": 1,
            "risk_level": {"id": 2, "name": "Alto"},
            "risk_level_modified_by_director": True,
        }

        result = await service.update_classification(
            1, CommentUpdate(risk_level=2), {"id": 7, "department_id": 1}
        )

        assert result["risk_level_modified_by_director"] is True
        mock_comments_repo.update_classification.assert_called_once_with(
            1, risk_level=2, pedagogical_category_ids=None
        )
        mock_audit_service.log.assert_called_once_with(
            action="UPDATE",
            entity_name="comments",
            entity_id=1,
            actor_id=7,
            description="El director modificó la clasificación del comentario 1",
        )

    @pytest.mark.asyncio
    async def test_update_classification_returns_none_when_update_fails(
        self, service, mock_comments_repo, mock_risk_levels_repo, mock_audit_service
    ):
        """Test update_classification returns None if the repository update finds nothing."""

        mock_comments_repo.get_department_id.return_value = 1
        mock_risk_levels_repo.get_by_id.return_value = {"id": 2, "name": "Alto"}
        mock_comments_repo.update_classification.return_value = None

        result = await service.update_classification(
            1, CommentUpdate(risk_level=2), {"id": 7, "department_id": 1}
        )

        assert result is None
        mock_audit_service.log.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_classification_notifies_teacher_of_risk_level_change(
        self,
        service,
        mock_comments_repo,
        mock_risk_levels_repo,
        mock_notification_service,
    ):
        """Test the evaluated teacher is notified, with a detailed diff, when the
        director actually changes the risk level."""

        mock_comments_repo.get_department_id.return_value = 1
        mock_risk_levels_repo.get_by_id.return_value = {"id": 2, "name": "Alto"}
        mock_comments_repo.update_classification.return_value = MagicMock()
        mock_comments_repo.get_teacher_user_id.return_value = 42
        mock_comments_repo.get_by_id_enriched.side_effect = [
            {
                "id": 1,
                "teacher_id": 9,
                "original_text": "Comentario del estudiante",
                "course_name": "Cálculo I",
                "group_name": "A",
                "risk_level": {"id": 1, "name": "Bajo"},
                "pedagogical_categories": [],
            },
            {
                "id": 1,
                "teacher_id": 9,
                "original_text": "Comentario del estudiante",
                "course_name": "Cálculo I",
                "group_name": "A",
                "risk_level": {"id": 2, "name": "Alto"},
                "pedagogical_categories": [],
            },
        ]

        await service.update_classification(
            1, CommentUpdate(risk_level=2), {"id": 7, "department_id": 1}
        )

        mock_notification_service.create.assert_called_once()
        payload = mock_notification_service.create.call_args.args[0]
        assert payload.user_id == 42
        assert 'de "Bajo" a "Alto"' in payload.message
        assert "Cálculo I" in payload.message
        assert payload.link == "/docentes/9"
        assert mock_notification_service.create.call_args.kwargs["actor_id"] == 7

    @pytest.mark.asyncio
    async def test_update_classification_notifies_teacher_of_category_change(
        self,
        service,
        mock_comments_repo,
        mock_pedagogical_categories_repo,
        mock_notification_service,
    ):
        """Test the notification describes pedagogical category changes too."""

        mock_comments_repo.get_department_id.return_value = 1
        mock_pedagogical_categories_repo.get_by_id.return_value = {
            "id": 3,
            "name": "Metodología",
        }
        mock_comments_repo.update_classification.return_value = MagicMock()
        mock_comments_repo.get_teacher_user_id.return_value = 42
        mock_comments_repo.get_by_id_enriched.side_effect = [
            {
                "id": 1,
                "teacher_id": 9,
                "original_text": "x",
                "risk_level": None,
                "pedagogical_categories": [{"id": 1, "name": "Claridad"}],
            },
            {
                "id": 1,
                "teacher_id": 9,
                "original_text": "x",
                "risk_level": None,
                "pedagogical_categories": [{"id": 3, "name": "Metodología"}],
            },
        ]

        await service.update_classification(
            1,
            CommentUpdate(pedagogical_category_ids=[3]),
            {"id": 7, "department_id": 1},
        )

        mock_notification_service.create.assert_called_once()
        payload = mock_notification_service.create.call_args.args[0]
        assert 'de "Claridad" a "Metodología"' in payload.message

    @pytest.mark.asyncio
    async def test_update_classification_skips_notification_when_nothing_changed(
        self,
        service,
        mock_comments_repo,
        mock_risk_levels_repo,
        mock_notification_service,
    ):
        """Test no notification is sent when the resulting classification is
        identical to what it was before (e.g. re-submitting the same value)."""

        mock_comments_repo.get_department_id.return_value = 1
        mock_risk_levels_repo.get_by_id.return_value = {"id": 2, "name": "Alto"}
        mock_comments_repo.update_classification.return_value = MagicMock()
        same_state = {
            "id": 1,
            "teacher_id": 9,
            "original_text": "x",
            "risk_level": {"id": 2, "name": "Alto"},
            "pedagogical_categories": [],
        }
        mock_comments_repo.get_by_id_enriched.side_effect = [same_state, same_state]

        await service.update_classification(
            1, CommentUpdate(risk_level=2), {"id": 7, "department_id": 1}
        )

        mock_notification_service.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_classification_notification_link_is_none_without_teacher_id(
        self,
        service,
        mock_comments_repo,
        mock_risk_levels_repo,
        mock_notification_service,
    ):
        """Test the notification link is omitted when the comment has no teacher_id."""

        mock_comments_repo.get_department_id.return_value = 1
        mock_risk_levels_repo.get_by_id.return_value = {"id": 2, "name": "Alto"}
        mock_comments_repo.update_classification.return_value = MagicMock()
        mock_comments_repo.get_teacher_user_id.return_value = 42
        mock_comments_repo.get_by_id_enriched.side_effect = [
            {
                "id": 1,
                "teacher_id": None,
                "original_text": "x",
                "risk_level": {"id": 1, "name": "Bajo"},
                "pedagogical_categories": [],
            },
            {
                "id": 1,
                "teacher_id": None,
                "original_text": "x",
                "risk_level": {"id": 2, "name": "Alto"},
                "pedagogical_categories": [],
            },
        ]

        await service.update_classification(
            1, CommentUpdate(risk_level=2), {"id": 7, "department_id": 1}
        )

        mock_notification_service.create.assert_called_once()
        payload = mock_notification_service.create.call_args.args[0]
        assert payload.link is None

    @pytest.mark.asyncio
    async def test_update_classification_skips_notification_when_teacher_has_no_user(
        self,
        service,
        mock_comments_repo,
        mock_risk_levels_repo,
        mock_notification_service,
    ):
        """Test the notification is skipped (not an error) when the teacher has
        no linked user account."""

        mock_comments_repo.get_department_id.return_value = 1
        mock_risk_levels_repo.get_by_id.return_value = {"id": 2, "name": "Alto"}
        mock_comments_repo.update_classification.return_value = MagicMock()
        mock_comments_repo.get_teacher_user_id.return_value = None
        mock_comments_repo.get_by_id_enriched.side_effect = [
            {
                "id": 1,
                "teacher_id": 9,
                "original_text": "x",
                "risk_level": {"id": 1, "name": "Bajo"},
                "pedagogical_categories": [],
            },
            {
                "id": 1,
                "teacher_id": 9,
                "original_text": "x",
                "risk_level": {"id": 2, "name": "Alto"},
                "pedagogical_categories": [],
            },
        ]

        await service.update_classification(
            1, CommentUpdate(risk_level=2), {"id": 7, "department_id": 1}
        )

        mock_notification_service.create.assert_not_called()
