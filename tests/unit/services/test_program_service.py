"""
Tests for ProgramService layer.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.exceptions import ResourceAlreadyExistsError
from api.models.program import ProgramModel
from api.schemas.program import ProgramCreate, ProgramFilters, ProgramUpdate
from api.services.program_service import ProgramService


class TestProgramService:
    """Test suite for ProgramService."""

    @pytest.fixture
    def mock_programs_repo(self):
        """Mock ProgramsRepository."""

        repo = MagicMock()
        repo.db = MagicMock()
        return repo

    @pytest.fixture
    def mock_audit_service(self):
        """Mock AuditService."""

        service = MagicMock()
        service.log = AsyncMock()
        return service

    @pytest.fixture
    def service(self, mock_programs_repo, mock_audit_service):
        """Create service instance with mocked dependencies."""

        return ProgramService(mock_programs_repo, mock_audit_service)

    @pytest.fixture
    def mock_program(self):
        """Mock ProgramModel instance."""

        program = MagicMock(spec=ProgramModel)
        program.id = 1
        program.name = "Ingeniería de Sistemas"
        program.code = "IS"
        program.active = True
        program.created_at = "2026-01-01T00:00:00Z"
        program.updated_at = "2026-01-01T00:00:00Z"
        return program

    @pytest.fixture
    def current_user(self):
        """Mock current user dict."""

        return {"id": 99, "roles": ["ADMIN"]}

    async def test_get_all_returns_paginated_programs(
        self, service, mock_programs_repo, mock_program
    ):
        """Test get_all returns the paginated envelope payload."""

        mock_programs_repo.search.return_value = ([mock_program], 1)

        filters = ProgramFilters()
        pagination = PaginationParams(page=1, limit=10)

        result = await service.get_all(filters, pagination)

        mock_programs_repo.search.assert_called_once_with(filters, pagination)
        assert result["total"] == 1
        assert result["page"] == 1
        assert result["limit"] == 10
        assert result["pages"] == 1
        assert result["items"][0]["code"] == "IS"

    async def test_get_all_when_empty_returns_zero_pages(
        self, service, mock_programs_repo
    ):
        """Test get_all reports zero pages when nothing matches."""

        mock_programs_repo.search.return_value = ([], 0)

        result = await service.get_all(
            ProgramFilters(search="nada"), PaginationParams(page=1, limit=10)
        )

        assert result["items"] == []
        assert result["total"] == 0
        assert result["pages"] == 0

    async def test_get_by_id_when_program_exists_returns_dict(
        self, service, mock_programs_repo, mock_program
    ):
        """Test get_by_id returns the serialized program when found."""

        mock_programs_repo.get.return_value = mock_program

        result = await service.get_by_id(1)

        mock_programs_repo.get.assert_called_once_with(1)
        assert result["id"] == 1
        assert result["name"] == "Ingeniería de Sistemas"

    async def test_get_by_id_when_program_missing_returns_none(
        self, service, mock_programs_repo
    ):
        """Test get_by_id returns None when not found."""

        mock_programs_repo.get.return_value = None

        result = await service.get_by_id(999)

        assert result is None

    async def test_create_with_valid_data_persists_and_audits(
        self,
        service,
        mock_programs_repo,
        mock_audit_service,
        mock_program,
        current_user,
    ):
        """Test create persists the program and logs the audit entry."""

        mock_programs_repo.get_by_code.return_value = None
        mock_programs_repo.create_program.return_value = mock_program

        data = ProgramCreate(name="Ingeniería de Sistemas", code="IS")

        result = await service.create(data, current_user)

        mock_programs_repo.get_by_code.assert_called_once_with("IS")
        mock_programs_repo.create_program.assert_called_once_with(data)
        mock_audit_service.log.assert_called_once()
        audit_kwargs = mock_audit_service.log.call_args.kwargs
        assert audit_kwargs["action"] == "CREATE"
        assert audit_kwargs["entity_name"] == "programs"
        assert audit_kwargs["entity_id"] == 1
        assert audit_kwargs["actor_id"] == 99
        assert result["code"] == "IS"

    async def test_create_with_duplicate_code_raises_error(
        self,
        service,
        mock_programs_repo,
        mock_audit_service,
        mock_program,
        current_user,
    ):
        """Test create raises when the code is already taken."""

        mock_programs_repo.get_by_code.return_value = mock_program

        data = ProgramCreate(name="Otro nombre", code="IS")

        with pytest.raises(ResourceAlreadyExistsError):
            await service.create(data, current_user)

        mock_programs_repo.create_program.assert_not_called()
        mock_audit_service.log.assert_not_called()

    async def test_update_with_valid_data_persists_and_audits(
        self,
        service,
        mock_programs_repo,
        mock_audit_service,
        mock_program,
        current_user,
    ):
        """Test update persists the change and logs the audit entry."""

        mock_programs_repo.get.return_value = mock_program
        mock_programs_repo.update_program.return_value = mock_program

        data = ProgramUpdate(name="Ingeniería Industrial")

        result = await service.update(1, data, current_user)

        mock_programs_repo.update_program.assert_called_once_with(mock_program, data)
        mock_audit_service.log.assert_called_once()
        assert result is not None

    async def test_update_records_changed_fields_in_audit_description(
        self,
        service,
        mock_programs_repo,
        mock_audit_service,
        mock_program,
        current_user,
    ):
        """Test the audit description names the fields that actually changed."""

        def _apply(program, data):
            for key, value in data.model_dump(exclude_unset=True).items():
                setattr(program, key, value)
            return program

        mock_programs_repo.get.return_value = mock_program
        mock_programs_repo.get_by_code.return_value = None
        mock_programs_repo.update_program.side_effect = _apply

        data = ProgramUpdate(name="Ingeniería Industrial", code="II", active=False)

        await service.update(1, data, current_user)

        description = mock_audit_service.log.call_args.kwargs["description"]
        assert (
            "name cambió de Ingeniería de Sistemas a Ingeniería Industrial"
            in description
        )
        assert "code cambió de IS a II" in description
        assert "active cambió de True a False" in description

    async def test_update_without_changes_records_no_changes(
        self,
        service,
        mock_programs_repo,
        mock_audit_service,
        mock_program,
        current_user,
    ):
        """Test the audit description says so when nothing changed."""

        mock_programs_repo.get.return_value = mock_program
        mock_programs_repo.update_program.return_value = mock_program

        await service.update(1, ProgramUpdate(), current_user)

        description = mock_audit_service.log.call_args.kwargs["description"]
        assert "No se realizaron cambios" in description

    async def test_update_when_program_missing_returns_none(
        self, service, mock_programs_repo, mock_audit_service, current_user
    ):
        """Test update returns None when the program does not exist."""

        mock_programs_repo.get.return_value = None

        result = await service.update(999, ProgramUpdate(name="X"), current_user)

        assert result is None
        mock_programs_repo.update_program.assert_not_called()
        mock_audit_service.log.assert_not_called()

    async def test_update_with_duplicate_code_raises_error(
        self, service, mock_programs_repo, mock_program, current_user
    ):
        """Test update raises when the new code belongs to another program."""

        other_program = MagicMock(spec=ProgramModel)
        other_program.id = 2
        other_program.code = "II"

        mock_programs_repo.get.return_value = mock_program
        mock_programs_repo.get_by_code.return_value = other_program

        with pytest.raises(ResourceAlreadyExistsError):
            await service.update(1, ProgramUpdate(code="II"), current_user)

        mock_programs_repo.update_program.assert_not_called()

    async def test_update_keeping_its_own_code_does_not_check_uniqueness(
        self, service, mock_programs_repo, mock_program, current_user
    ):
        """Test resending the program's own code is not treated as a duplicate."""

        mock_programs_repo.get.return_value = mock_program
        mock_programs_repo.update_program.return_value = mock_program

        result = await service.update(1, ProgramUpdate(code="IS"), current_user)

        mock_programs_repo.get_by_code.assert_not_called()
        assert result is not None

    async def test_delete_when_program_exists_removes_and_audits(
        self,
        service,
        mock_programs_repo,
        mock_audit_service,
        mock_program,
        current_user,
    ):
        """Test delete removes the program and logs the audit entry."""

        mock_programs_repo.get.return_value = mock_program

        result = await service.delete(1, current_user)

        mock_programs_repo.delete_program.assert_called_once_with(mock_program)
        mock_audit_service.log.assert_called_once()
        assert mock_audit_service.log.call_args.kwargs["action"] == "DELETE"
        assert result["code"] == "IS"

    async def test_delete_when_program_missing_returns_none(
        self, service, mock_programs_repo, mock_audit_service, current_user
    ):
        """Test delete returns None when the program does not exist."""

        mock_programs_repo.get.return_value = None

        result = await service.delete(999, current_user)

        assert result is None
        mock_programs_repo.delete_program.assert_not_called()
        mock_audit_service.log.assert_not_called()
