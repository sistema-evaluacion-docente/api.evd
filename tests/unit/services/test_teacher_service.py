"""
Tests for TeacherService layer.
"""

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.core.pagination import PaginationParams
from api.exceptions import (
    PermissionDeniedError,
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
    ValidationError,
)
from api.models.teacher import TeacherModel
from api.schemas.teacher import (
    TeacherCreate,
    TeacherCreateWithUser,
    TeacherFilters,
    TeacherUpdate,
)
from api.services.teacher_service import TeacherService


class TestTeacherService:
    """Test suite for TeacherService."""

    @pytest.fixture
    def mock_teachers_repo(self):
        """Mock TeachersRepository."""

        repo = MagicMock()
        repo.db = MagicMock()
        return repo

    @pytest.fixture
    def mock_users_repo(self):
        """Mock UsersRepository."""

        return MagicMock()

    @pytest.fixture
    def mock_audit_service(self):
        """Mock AuditService."""

        service = MagicMock()
        service.log = AsyncMock()
        return service

    @pytest.fixture
    def mock_periods_repo(self):
        """Mock AcademicPeriodsRepository."""

        repo = MagicMock()
        repo.get_by_id = AsyncMock()
        repo.get_previous_period_code = AsyncMock()
        repo.get_by_code = AsyncMock()
        return repo

    @pytest.fixture
    def mock_user_service(self):
        """Mock UserService."""

        service = MagicMock()
        service.create_user_with_roles = AsyncMock()
        return service

    @pytest.fixture
    def service(
        self,
        mock_teachers_repo,
        mock_users_repo,
        mock_audit_service,
        mock_periods_repo,
        mock_user_service,
    ):
        """Create service instance with mocked dependencies."""

        return TeacherService(
            mock_teachers_repo,
            mock_users_repo,
            mock_audit_service,
            mock_periods_repo,
            mock_user_service,
        )

    @pytest.fixture
    def mock_teacher(self):
        """Mock TeacherModel instance."""

        teacher = MagicMock(spec=TeacherModel)
        teacher.id = 1
        teacher.department_id = 1
        teacher.contract_type = "FULL_TIME"
        teacher.user_id = 1
        teacher.active = True
        teacher.user = MagicMock()
        teacher.user.institutional_code = "12345"
        teacher.created_at = "2024-01-01T00:00:00Z"
        teacher.updated_at = "2024-01-01T00:00:00Z"
        return teacher

    @pytest.fixture
    def current_user(self):
        """Mock current user dict."""

        return {"id": 99, "roles": ["ADMIN"]}

    @pytest.mark.asyncio
    async def test_get_all_returns_paginated_teachers(
        self, service, mock_teachers_repo, mock_teacher
    ):
        """Test get_all returns paginated teachers."""

        mock_teachers_repo.search.return_value = ([mock_teacher], 1)
        mock_teachers_repo.get_user_role_names = MagicMock(return_value=["DOCENTE"])

        filters = TeacherFilters()
        pagination = PaginationParams(page=1, limit=10)

        result = await service.get_all(filters, pagination)

        assert result["total"] == 1
        assert result["page"] == 1
        assert result["limit"] == 10
        assert len(result["items"]) == 1

    @pytest.mark.asyncio
    async def test_get_all_with_averages(
        self, service, mock_teachers_repo, mock_teacher
    ):
        """Test get_all_with_averages includes overall_average and
        high_risk_comments_count from the batched
        (teacher, avg_score, high_risk_count) rows search_with_averages returns."""

        mock_teachers_repo.search_with_averages.return_value = (
            [(mock_teacher, 4.5, 3)],
            1,
        )

        filters = TeacherFilters()
        pagination = PaginationParams(page=1, limit=10)

        result = await service.get_all_with_averages(filters, pagination, 1)

        assert result["items"][0]["overall_average"] == 4.5
        assert result["items"][0]["high_risk_comments_count"] == 3
        mock_teachers_repo.search_with_averages.assert_called_once_with(
            filters, pagination, 1, True, None
        )

    @pytest.mark.asyncio
    async def test_get_all_with_averages_restricts_the_figures_to_one_modality(
        self, service, mock_teachers_repo, mock_teacher
    ):
        """Test the modality reaches the repository, which narrows both figures."""

        mock_teachers_repo.search_with_averages.return_value = (
            [(mock_teacher, 4.0, 0)],
            1,
        )

        filters = TeacherFilters()
        pagination = PaginationParams(page=1, limit=10)

        await service.get_all_with_averages(filters, pagination, 1, True, "distancia")

        mock_teachers_repo.search_with_averages.assert_called_once_with(
            filters, pagination, 1, True, "DISTANCIA"
        )

    @pytest.mark.asyncio
    async def test_get_all_with_averages_rejects_an_unknown_modality(
        self, service, mock_teachers_repo
    ):
        """Test a modality outside the catalog never reaches the repository."""

        filters = TeacherFilters()
        pagination = PaginationParams(page=1, limit=10)

        with pytest.raises(ValidationError):
            await service.get_all_with_averages(
                filters, pagination, 1, True, "VIRTUAL"
            )

        mock_teachers_repo.search_with_averages.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_all_batches_role_lookup(
        self, service, mock_teachers_repo, mock_users_repo, mock_teacher
    ):
        """Test get_all fetches roles for all teachers in one bulk call instead
        of one query per teacher."""

        mock_teachers_repo.search.return_value = ([mock_teacher], 1)
        mock_users_repo.get_user_role_names_bulk.return_value = {1: ["DOCENTE"]}

        filters = TeacherFilters()
        pagination = PaginationParams(page=1, limit=10)

        await service.get_all(filters, pagination)

        mock_users_repo.get_user_role_names_bulk.assert_called_once_with([1])
        mock_users_repo.get_user_role_names.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, service, mock_teachers_repo, mock_teacher):
        """Test get_by_id returns teacher dict when found."""

        mock_teachers_repo.get_by_id.return_value = mock_teacher

        result = await service.get_by_id(1)

        assert result is not None
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service, mock_teachers_repo):
        """Test get_by_id returns None when not found."""

        mock_teachers_repo.get_by_id.return_value = None

        result = await service.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_create_teacher_success(
        self,
        service,
        mock_teachers_repo,
        mock_user_service,
        mock_audit_service,
        mock_teacher,
        current_user,
    ):
        """Test create succeeds with valid data."""

        mock_teachers_repo.get_by_institutional_code.side_effect = [None, mock_teacher]
        mock_user_service.create_user_with_roles.return_value = {"id": 1}

        data = TeacherCreate(
            institutional_code="12345",
            department_id=1,
            contract_type="FULL_TIME",
        )

        result = await service.create(data, current_user)

        assert result is not None
        mock_user_service.create_user_with_roles.assert_called_once()
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_teacher_duplicate_code_raises(
        self, service, mock_teachers_repo, mock_teacher
    ):
        """Test create raises when institutional_code already exists."""

        mock_teachers_repo.get_by_institutional_code.return_value = mock_teacher

        data = TeacherCreate(institutional_code="12345")

        with pytest.raises(ResourceAlreadyExistsError):
            await service.create(data, {"id": 99})

    @pytest.mark.asyncio
    async def test_create_with_user_success(
        self,
        service,
        mock_teachers_repo,
        mock_users_repo,
        mock_user_service,
        mock_audit_service,
        mock_teacher,
        current_user,
    ):
        """Test create_with_user creates user and teacher."""

        mock_teachers_repo.get_by_institutional_code.side_effect = [None, mock_teacher]
        mock_users_repo.get_by_email.return_value = None

        data = TeacherCreateWithUser(
            email="test@example.com",
            name="Test Teacher",
            institutional_code="12345",
        )

        result = await service.create_with_user(data, current_user)

        assert result is not None
        mock_user_service.create_user_with_roles.assert_called_once()
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_with_user_duplicate_code_raises(
        self, service, mock_teachers_repo, mock_teacher
    ):
        """Test create_with_user raises when institutional_code exists."""

        mock_teachers_repo.get_by_institutional_code.return_value = mock_teacher

        data = TeacherCreateWithUser(
            email="test@example.com",
            name="Test",
            institutional_code="12345",
        )

        with pytest.raises(ResourceAlreadyExistsError):
            await service.create_with_user(data, {"id": 99})

    @pytest.mark.asyncio
    async def test_update_teacher_success(
        self,
        service,
        mock_teachers_repo,
        mock_audit_service,
        mock_teacher,
        current_user,
    ):
        """Test update succeeds when teacher exists."""

        mock_teachers_repo.get_by_id.return_value = mock_teacher
        mock_teachers_repo.update_teacher.return_value = mock_teacher

        data = TeacherUpdate(contract_type="PART_TIME")

        result = await service.update(1, data, current_user)

        assert result is not None
        mock_teachers_repo.update_teacher.assert_called_once()
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_teacher_not_found(
        self, service, mock_teachers_repo, current_user
    ):
        """Test update returns None when teacher not found."""

        mock_teachers_repo.get_by_id.return_value = None

        data = TeacherUpdate(contract_type="PART_TIME")

        result = await service.update(999, data, current_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_teacher_success(
        self,
        service,
        mock_teachers_repo,
        mock_audit_service,
        mock_teacher,
        current_user,
    ):
        """Test delete succeeds when teacher exists."""

        mock_teachers_repo.get_by_id.return_value = mock_teacher

        result = await service.delete(1, current_user)

        assert result is not None
        mock_teachers_repo.delete_teacher.assert_called_once_with(1)
        mock_audit_service.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_teacher_not_found(
        self, service, mock_teachers_repo, current_user
    ):
        """Test delete returns None when teacher not found."""

        mock_teachers_repo.get_by_id.return_value = None

        result = await service.delete(999, current_user)

        assert result is None

    @pytest.mark.asyncio
    async def test_count_by_department(
        self, service, mock_teachers_repo, mock_periods_repo
    ):
        """Test count_by_department delegates to repository."""

        mock_periods_repo.get_by_id.return_value = {"code": "2025-1"}
        mock_periods_repo.get_previous_period_code.return_value = "2024-2"
        mock_periods_repo.get_by_code.return_value = MagicMock(id=2)
        mock_teachers_repo.count_by_department.return_value = {
            "current_count": 10,
            "previous_count": 8,
        }

        result = await service.count_by_department(1, 1)

        assert result["current_count"] == 10
        assert result["previous_count"] == 8

    @pytest.mark.asyncio
    async def test_get_history(self, service, mock_teachers_repo, mock_users_repo):
        """Test get_history delegates to repository with pagination and sort_by."""

        pagination = PaginationParams(page=1, limit=10)
        mock_teachers_repo.get_history.return_value = (
            [
                {
                    "evaluation_id": 1,
                    "period_id": 1,
                    "period_code": "2024-1",
                    "period_name": "Period 1",
                    "overall_average": 4.5,
                    "group_count": 3,
                }
            ],
            1,
            {
                "teacher_id": 1,
                "institutional_code": "12345",
                "name": "Test Teacher",
            },
        )
        mock_teachers_repo.get_by_id.return_value = MagicMock()

        mock_user = MagicMock()
        mock_user.id = 99
        mock_users_repo.get_by_uid.return_value = mock_user
        mock_users_repo.get_user_role_names.return_value = ["ADMIN"]

        current_user = MagicMock()
        current_user.uid = "test-uid"

        result = await service.get_history(
            current_user, 1, pagination, "overall_average_desc"
        )

        assert result["teacher_id"] == 1
        assert result["institutional_code"] == "12345"
        assert result["total"] == 1
        assert result["page"] == 1
        assert result["limit"] == 10
        assert result["pages"] == 1
        assert len(result["items"]) == 1
        mock_teachers_repo.get_history.assert_called_once_with(
            1, pagination, "overall_average_desc"
        )

    # ------------------------------------------------------------------ #
    # get_evaluation_report
    # ------------------------------------------------------------------ #
    @pytest.fixture
    def mock_evaluations_repo(self):
        """Mock EvaluationsRepository."""

        return MagicMock()

    @pytest.fixture
    def service_with_evaluations(
        self,
        mock_teachers_repo,
        mock_users_repo,
        mock_audit_service,
        mock_periods_repo,
        mock_user_service,
        mock_evaluations_repo,
    ):
        """A TeacherService wired with an EvaluationsRepository."""

        return TeacherService(
            mock_teachers_repo,
            mock_users_repo,
            mock_audit_service,
            mock_periods_repo,
            mock_user_service,
            evaluations_repository=mock_evaluations_repo,
        )

    @pytest.fixture
    def report_current_user(self):
        """TokenUser-like object for the report endpoint."""

        user = MagicMock()
        user.uid = "docente-uid"
        return user

    @pytest.mark.asyncio
    async def test_get_evaluation_report_user_or_teacher_missing(
        self, service, mock_teachers_repo, mock_users_repo, report_current_user
    ):
        """Test a missing user or teacher raises ResourceNotFoundError."""

        mock_users_repo.get_by_uid.return_value = None
        mock_teachers_repo.get_by_id.return_value = None

        with pytest.raises(ResourceNotFoundError):
            await service.get_evaluation_report(1, 1, report_current_user)

    @pytest.mark.asyncio
    async def test_get_evaluation_report_forbidden_for_another_teacher(
        self,
        service,
        mock_teachers_repo,
        mock_users_repo,
        mock_teacher,
        report_current_user,
    ):
        """Test a DOCENTE cannot fetch another teacher's report."""

        user = MagicMock(id=5)
        mock_users_repo.get_by_uid.return_value = user
        mock_teacher.user_id = 999  # not the caller
        mock_teachers_repo.get_by_id.return_value = mock_teacher
        mock_users_repo.get_user_role_names.return_value = ["DOCENTE"]

        with pytest.raises(PermissionDeniedError):
            await service.get_evaluation_report(1, 1, report_current_user)

    @pytest.mark.asyncio
    async def test_get_evaluation_report_forbidden_for_a_director_of_another_department(
        self,
        service,
        mock_teachers_repo,
        mock_users_repo,
        mock_teacher,
        report_current_user,
    ):
        """Test a director outside the teacher's department is forbidden."""

        user = MagicMock(id=5)
        mock_users_repo.get_by_uid.return_value = user
        mock_teacher.department_id = 1
        mock_teachers_repo.get_by_id.return_value = mock_teacher
        mock_users_repo.get_user_role_names.return_value = [
            "DIRECTOR DE DEPARTAMENTO"
        ]
        mock_users_repo.get_director_by_user_id.return_value = MagicMock(
            department_id=2
        )

        with pytest.raises(PermissionDeniedError):
            await service.get_evaluation_report(1, 1, report_current_user)

    @pytest.mark.asyncio
    async def test_get_evaluation_report_without_evaluations_repository(
        self,
        service,
        mock_teachers_repo,
        mock_users_repo,
        mock_teacher,
        report_current_user,
    ):
        """Test the report raises when no EvaluationsRepository was wired."""

        user = MagicMock(id=5)
        mock_users_repo.get_by_uid.return_value = user
        mock_teacher.user_id = 5
        mock_teachers_repo.get_by_id.return_value = mock_teacher
        mock_users_repo.get_user_role_names.return_value = ["DOCENTE"]

        with pytest.raises(ValidationError):
            await service.get_evaluation_report(1, 1, report_current_user)

    @pytest.mark.asyncio
    async def test_get_evaluation_report_evaluation_not_found(
        self,
        service_with_evaluations,
        mock_teachers_repo,
        mock_users_repo,
        mock_evaluations_repo,
        mock_teacher,
        report_current_user,
    ):
        """Test a missing evaluation raises ResourceNotFoundError."""

        user = MagicMock(id=5)
        mock_users_repo.get_by_uid.return_value = user
        mock_teacher.user_id = 5
        mock_teachers_repo.get_by_id.return_value = mock_teacher
        mock_users_repo.get_user_role_names.return_value = ["DOCENTE"]
        mock_evaluations_repo.get_by_id.return_value = None

        with pytest.raises(ResourceNotFoundError):
            await service_with_evaluations.get_evaluation_report(
                1, 1, report_current_user
            )

    @pytest.mark.asyncio
    async def test_get_evaluation_report_without_a_pdf(
        self,
        service_with_evaluations,
        mock_teachers_repo,
        mock_users_repo,
        mock_evaluations_repo,
        mock_teacher,
        report_current_user,
    ):
        """Test an evaluation without a PDF raises ResourceNotFoundError."""

        user = MagicMock(id=5)
        mock_users_repo.get_by_uid.return_value = user
        mock_teacher.user_id = 5
        mock_teachers_repo.get_by_id.return_value = mock_teacher
        mock_users_repo.get_user_role_names.return_value = ["DOCENTE"]
        mock_evaluations_repo.get_by_id.return_value = MagicMock(pdf_url=None)

        with patch(
            "api.utils.evaluation_pdfs.split_pdf_urls", return_value=[]
        ):
            with pytest.raises(ResourceNotFoundError):
                await service_with_evaluations.get_evaluation_report(
                    1, 1, report_current_user
                )

    @pytest.mark.asyncio
    async def test_get_evaluation_report_without_institutional_code(
        self,
        service_with_evaluations,
        mock_teachers_repo,
        mock_users_repo,
        mock_evaluations_repo,
        mock_teacher,
        report_current_user,
    ):
        """Test a teacher without an institutional code raises ResourceNotFoundError."""

        user = MagicMock(id=5)
        mock_users_repo.get_by_uid.return_value = user
        mock_teacher.user_id = 5
        mock_teacher.user.institutional_code = None
        mock_teachers_repo.get_by_id.return_value = mock_teacher
        mock_users_repo.get_user_role_names.return_value = ["DOCENTE"]
        mock_evaluations_repo.get_by_id.return_value = MagicMock(pdf_url="a.pdf")

        with patch(
            "api.utils.evaluation_pdfs.split_pdf_urls", return_value=["a.pdf"]
        ):
            with pytest.raises(ResourceNotFoundError):
                await service_with_evaluations.get_evaluation_report(
                    1, 1, report_current_user
                )

    @pytest.mark.asyncio
    async def test_get_evaluation_report_teacher_missing_from_pdf(
        self,
        service_with_evaluations,
        mock_teachers_repo,
        mock_users_repo,
        mock_evaluations_repo,
        mock_teacher,
        report_current_user,
    ):
        """Test extract_teacher_pages returning None becomes a 404."""

        user = MagicMock(id=5)
        mock_users_repo.get_by_uid.return_value = user
        mock_teacher.user_id = 5
        mock_teachers_repo.get_by_id.return_value = mock_teacher
        mock_users_repo.get_user_role_names.return_value = ["DOCENTE"]
        mock_evaluations_repo.get_by_id.return_value = MagicMock(pdf_url="a.pdf")

        with patch(
            "api.utils.evaluation_pdfs.split_pdf_urls", return_value=["a.pdf"]
        ), patch(
            "api.utils.pdf_extractor.extract_teacher_pages", return_value=None
        ):
            with pytest.raises(ResourceNotFoundError):
                await service_with_evaluations.get_evaluation_report(
                    1, 1, report_current_user
                )

    @pytest.mark.asyncio
    async def test_get_evaluation_report_success(
        self,
        service_with_evaluations,
        mock_teachers_repo,
        mock_users_repo,
        mock_evaluations_repo,
        mock_teacher,
        report_current_user,
    ):
        """Test the happy path returns the extracted PDF bytes."""

        user = MagicMock(id=5)
        mock_users_repo.get_by_uid.return_value = user
        mock_teacher.user_id = 5
        mock_teachers_repo.get_by_id.return_value = mock_teacher
        mock_users_repo.get_user_role_names.return_value = ["DOCENTE"]
        mock_evaluations_repo.get_by_id.return_value = MagicMock(pdf_url="a.pdf")

        with patch(
            "api.utils.evaluation_pdfs.split_pdf_urls", return_value=["a.pdf"]
        ), patch(
            "api.utils.pdf_extractor.extract_teacher_pages", return_value=b"%PDF-1.4"
        ):
            result = await service_with_evaluations.get_evaluation_report(
                1, 1, report_current_user
            )

        assert result == b"%PDF-1.4"

    # ------------------------------------------------------------------ #
    # _parse_csv / _parse_excel
    # ------------------------------------------------------------------ #
    def test_parse_csv_returns_rows_as_tuples(self):
        """Test _parse_csv turns raw bytes into a list of row tuples."""

        content = "nombre,email,codigo,contrato\nAna,ana@x.com,101,TC\n".encode(
            "utf-8-sig"
        )

        rows = TeacherService._parse_csv(content)

        assert rows[0] == ("nombre", "email", "codigo", "contrato")
        assert rows[1] == ("Ana", "ana@x.com", "101", "TC")

    def test_parse_excel_returns_rows_as_tuples(self):
        """Test _parse_excel reads a real workbook's rows."""

        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["nombre", "email", "codigo", "contrato"])
        ws.append(["Ana", "ana@x.com", "101", "TC"])
        buffer = io.BytesIO()
        wb.save(buffer)

        rows = TeacherService._parse_excel(buffer.getvalue())

        assert rows[0] == ("nombre", "email", "codigo", "contrato")
        assert rows[1] == ("Ana", "ana@x.com", "101", "TC")

    # ------------------------------------------------------------------ #
    # upload_excel
    # ------------------------------------------------------------------ #
    @pytest.mark.asyncio
    async def test_upload_excel_too_few_rows_raises(self, service, current_user):
        """Test a file with only a header raises ValidationError."""

        content = "nombre,email,codigo,contrato\n".encode("utf-8-sig")

        with pytest.raises(ValidationError):
            await service.upload_excel(content, "teachers.csv", 1, current_user)

    @pytest.mark.asyncio
    async def test_upload_excel_missing_columns_raises(self, service, current_user):
        """Test a file missing a required column raises ValidationError."""

        content = "nombre,email,codigo\nAna,ana@x.com,101\n".encode("utf-8-sig")

        with pytest.raises(ValidationError):
            await service.upload_excel(content, "teachers.csv", 1, current_user)

    @pytest.mark.asyncio
    async def test_upload_excel_creates_skips_and_reports_errors(
        self,
        service,
        mock_teachers_repo,
        mock_users_repo,
        mock_user_service,
        mock_audit_service,
        current_user,
    ):
        """Test the full import pipeline: created/skipped/error rows and the audit log."""

        csv_text = (
            "nombre,email,codigo,contrato\n"
            "Ana Perez,ana@x.com,101,TC\n"
            "Dora Lopez,dora@x.com,111,TC\n"
            "\n"
            "Emi Cruz,existing@x.com,106,TC\n"
            ",falta@x.com,105,TC\n"
            "Bea Ruiz,bea@x.com,102,TC\n"
            "Caro Diaz,caro@x.com,103,TC\n"
        )
        content = csv_text.encode("utf-8-sig")

        existing_teacher = MagicMock()
        existing_teacher.user = MagicMock(institutional_code="111")
        mock_teachers_repo.get_by_institutional_codes.return_value = [
            existing_teacher
        ]

        def _get_by_email(email):
            return MagicMock(id=1) if email == "existing@x.com" else None

        mock_users_repo.get_by_email.side_effect = _get_by_email

        mock_user_service.create_user_with_roles = AsyncMock(
            side_effect=[
                {"id": 10},
                ValueError("Rol inválido"),
                Exception("boom"),
            ]
        )

        result = await service.upload_excel(
            content, "teachers.csv", 7, current_user
        )

        assert len(result["created"]) == 1
        assert result["created"][0]["email"] == "ana@x.com"
        assert len(result["skipped"]) == 3
        assert len(result["errors"]) == 2
        mock_audit_service.log.assert_awaited_once()
