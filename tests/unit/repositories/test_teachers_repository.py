"""
Tests for TeachersRepository layer.
"""

from unittest.mock import MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.models.teacher import TeacherModel
from api.repositories.base import BaseRepository
from api.repositories.teachers import TeachersRepository
from api.schemas.teacher import TeacherFilters


class TestTeachersRepository:
    """Test suite for TeachersRepository."""

    @pytest.fixture
    def repo(self, mock_db):
        """Create repository instance with mocked DB."""

        return TeachersRepository(mock_db)

    @pytest.fixture
    def mock_teacher_model(self):
        """Mock TeacherModel instance."""

        teacher = MagicMock(spec=TeacherModel)
        teacher.id = 1
        teacher.department_id = 1
        teacher.contract_type = "FULL_TIME"
        teacher.user_id = 1
        teacher.active = True
        teacher.user = MagicMock()
        teacher.user.institutional_code = "12345"
        return teacher

    def test_inherits_base_repository(self, repo):
        """Test TeachersRepository inherits from BaseRepository."""

        assert isinstance(repo, BaseRepository)

    def test_get_by_id_found(self, repo, mock_db, mock_teacher_model):
        """Test get_by_id returns teacher when found."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value.first.return_value = mock_teacher_model

        result = repo.get_by_id(1)

        assert result == mock_teacher_model
        mock_db.query.assert_called_once_with(TeacherModel)

    def test_get_by_id_not_found(self, repo, mock_db):
        """Test get_by_id returns None when teacher not found."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None

        result = repo.get_by_id(999)

        assert result is None

    def test_get_by_institutional_code_found(self, repo, mock_db, mock_teacher_model):
        """Test get_by_institutional_code returns teacher when found."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value.first.return_value = mock_teacher_model

        result = repo.get_by_institutional_code("12345")

        assert result == mock_teacher_model

    def test_get_by_institutional_code_not_found(self, repo, mock_db):
        """Test get_by_institutional_code returns None when not found."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None

        result = repo.get_by_institutional_code("99999")

        assert result is None

    def test_get_by_institutional_codes_empty(self, repo, mock_db):
        """Test get_by_institutional_codes returns empty list for empty input."""

        result = repo.get_by_institutional_codes([])

        assert result == []

    def test_get_by_institutional_codes(self, repo, mock_db, mock_teacher_model):
        """Test get_by_institutional_codes returns matching teachers."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value.all.return_value = [mock_teacher_model]

        result = repo.get_by_institutional_codes(["12345"])

        assert len(result) == 1
        assert result[0] == mock_teacher_model

    def test_search_no_filters(self, repo, mock_db, mock_teacher_model):
        """Test search with no filters returns all teachers paginated."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_teacher_model
        ]

        filters = TeacherFilters()
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1
        assert items == [mock_teacher_model]
        mock_query.count.assert_called_once()
        mock_query.offset.assert_called_once_with(0)

    def test_search_with_search_filter(self, repo, mock_db, mock_teacher_model):
        """Test search applies ilike filter for search term."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_teacher_model
        ]

        filters = TeacherFilters(search="12345")
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1
        mock_query.filter.assert_called_once()

    def test_search_with_active_filter(self, repo, mock_db, mock_teacher_model):
        """Test search applies equality filter for active status."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_teacher_model
        ]

        filters = TeacherFilters(active=True)
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1

    def test_search_with_department_filter(self, repo, mock_db, mock_teacher_model):
        """Test search applies filter for department_id."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_teacher_model
        ]

        filters = TeacherFilters(department_id=1)
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1

    def test_search_with_contract_type_filter(self, repo, mock_db, mock_teacher_model):
        """Test search applies filter for contract_type."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_teacher_model
        ]

        filters = TeacherFilters(contract_type="FULL_TIME")
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1

    def test_search_pagination_offset(self, repo, mock_db, mock_teacher_model):
        """Test search calculates correct offset for page > 1."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 25
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_teacher_model
        ]

        filters = TeacherFilters()
        pagination = PaginationParams(page=3, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 25
        mock_query.offset.assert_called_once_with(20)

    def test_update_teacher(self, repo, mock_db, mock_teacher_model):
        """Test update_teacher updates teacher attributes."""

        result = repo.update_teacher(mock_teacher_model, {"contract_type": "PART_TIME"})

        assert mock_teacher_model.contract_type == "PART_TIME"
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_teacher_model)
        assert result == mock_teacher_model

    def test_delete_teacher_success(self, repo, mock_db, mock_teacher_model):
        """Test delete_teacher deletes and returns teacher."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value.first.return_value = mock_teacher_model

        result = repo.delete_teacher(1)

        assert result == mock_teacher_model
        mock_db.delete.assert_called_once_with(mock_teacher_model)
        mock_db.commit.assert_called_once()

    def test_delete_teacher_not_found(self, repo, mock_db):
        """Test delete_teacher returns None when not found."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None

        result = repo.delete_teacher(999)

        assert result is None

    def test_search_with_averages_sort_by_name(self, repo, mock_db, mock_teacher_model):
        """Test search_with_averages also honors non-average sort_by values, since
        it's now the single query used for every /teachers/with-averages request
        regardless of sort order (the avg_score is always selected in-query)."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            (mock_teacher_model, 4.5, 2)
        ]

        filters = TeacherFilters(sort_by="name_asc")
        pagination = PaginationParams(page=1, limit=10)

        rows, total = repo.search_with_averages(filters, pagination, 1)

        assert total == 1
        assert rows == [(mock_teacher_model, 4.5, 2)]
        mock_query.order_by.assert_called_once()

    def test_search_with_averages_sort_by_high_risk_comments(
        self, repo, mock_db, mock_teacher_model
    ):
        """Test search_with_averages honors sort_by=high_risk_comments_(asc|desc)."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.outerjoin.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            (mock_teacher_model, 4.5, 5)
        ]

        filters = TeacherFilters(sort_by="high_risk_comments_desc")
        pagination = PaginationParams(page=1, limit=10)

        rows, total = repo.search_with_averages(filters, pagination, 1)

        assert total == 1
        assert rows == [(mock_teacher_model, 4.5, 5)]
        mock_query.order_by.assert_called_once()


class TestGetHistory:
    """TeachersRepository.get_history against a real (in-memory SQLite) schema."""

    @pytest.fixture
    def db(self):
        """A session over every model's table, with one teacher evaluated in
        three periods: two groups (4.0 and 5.0) in 2024-1, one (3.0) in 2024-2
        and one (4.0) in 2025-1."""

        import importlib
        import pkgutil

        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        import api.models as models_pkg
        from api.database import Base
        from api.models.academic_group import AcademicGroupModel
        from api.models.academic_period import AcademicPeriodModel
        from api.models.evaluation import EvaluationModel
        from api.models.evaluation_score import EvaluationScoreModel
        from api.models.user import UserModel

        for module in pkgutil.iter_modules(models_pkg.__path__):
            importlib.import_module(f"api.models.{module.name}")

        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()

        user = UserModel(email="t@ufps.edu.co", name="T", institutional_code="05647")
        session.add(user)
        session.flush()
        teacher = TeacherModel(user_id=user.id)
        session.add(teacher)
        session.flush()

        for code, scores in (("2024-1", [4.0, 5.0]), ("2024-2", [3.0]), ("2025-1", [4.0])):
            period = AcademicPeriodModel(code=code, name=code, active=True)
            session.add(period)
            session.flush()
            evaluation = EvaluationModel(academic_period_id=period.id, active=True)
            session.add(evaluation)
            session.flush()

            for score in scores:
                group = AcademicGroupModel(teacher_id=teacher.id, academic_period_id=period.id)
                session.add(group)
                session.flush()
                session.add(
                    EvaluationScoreModel(
                        evaluation_id=evaluation.id,
                        academic_group_id=group.id,
                        respondent_count=10,
                        overall_average=score,
                    )
                )

        session.commit()
        session.teacher_id = teacher.id
        yield session
        session.close()

    def test_historical_average_weighs_each_period_the_same(self, db):
        """Test the mean is over the period averages (4.5, 3.0, 4.0), not the groups."""

        _, _, info = TeachersRepository(db).get_history(
            db.teacher_id, PaginationParams(page=1, limit=10)
        )

        assert info["historical_average"] == pytest.approx((4.5 + 3.0 + 4.0) / 3)

    def test_historical_average_covers_every_period_not_just_the_page(self, db):
        """Test a one-period page still reports the average of all three."""

        items, total, info = TeachersRepository(db).get_history(
            db.teacher_id, PaginationParams(page=1, limit=1)
        )

        assert len(items) == 1
        assert total == 3
        assert info["historical_average"] == pytest.approx((4.5 + 3.0 + 4.0) / 3)

    def test_historical_average_is_none_without_evaluations(self, db):
        """Test a teacher never evaluated has no historical average."""

        teacher = TeacherModel()
        db.add(teacher)
        db.commit()

        items, total, info = TeachersRepository(db).get_history(
            teacher.id, PaginationParams(page=1, limit=10)
        )

        assert (items, total) == ([], 0)
        assert info["historical_average"] is None
