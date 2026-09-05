"""Tests for ImprovementPlanEvidencesRepository layer."""

from unittest.mock import MagicMock

import pytest

from api.repositories.base import BaseRepository
from api.repositories.improvement_plan_evidences import (
    ImprovementPlanEvidencesRepository,
)
from api.schemas.improvement_plan import (
    ImprovementPlanEvidenceRequestCreate,
    ImprovementPlanEvidenceRequestUpdate,
    EvidenceRequestStatus,
)


def _make_request(request_id=1, plan_id=1, comments=None, evidences=None):
    """Build a bare evidence-request mock with the fields the serializer reads."""

    request = MagicMock()
    request.id = request_id
    request.plan_id = plan_id
    request.item_id = None
    request.requested_by = 2
    request.title = "Rúbrica"
    request.description = None
    request.status = "PENDIENTE"
    request.due_date = None
    request.comments = comments or []
    request.evidences = evidences or []
    return request


def _make_evidence(evidence_id=1, uploaded_by=3):
    evidence = MagicMock()
    evidence.id = evidence_id
    evidence.plan_id = 1
    evidence.item_id = None
    evidence.request_id = 1
    evidence.uploaded_by = uploaded_by
    evidence.description = None
    evidence.file_url = "/tmp/e.pdf"
    evidence.status = "PENDIENTE"
    evidence.reviewed_by = None
    evidence.reviewed_at = None
    evidence.created_at = None
    return evidence


def _make_comment(comment_id=1, author_id=3):
    comment = MagicMock()
    comment.id = comment_id
    comment.request_id = 1
    comment.author_id = author_id
    comment.body = "Listo"
    comment.is_system = False
    comment.created_at = None
    return comment


class TestImprovementPlanEvidencesRepository:
    """Test suite for ImprovementPlanEvidencesRepository."""

    @pytest.fixture
    def repo(self, mock_db):
        """Create repository instance with mocked DB."""

        return ImprovementPlanEvidencesRepository(mock_db)

    def test_inherits_base_repository(self, repo):
        """Test ImprovementPlanEvidencesRepository inherits from BaseRepository."""

        assert isinstance(repo, BaseRepository)

    def test_get_request_found(self, repo, mock_db):
        """Test get_request returns the matching request."""

        request = _make_request()
        mock_db.query.return_value.filter.return_value.first.return_value = request

        result = repo.get_request(1, 1)

        assert result == request

    @pytest.mark.asyncio
    async def test_list_requests_enriches_every_row(self, repo, mock_db):
        """Test list_requests enriches every request with author names."""

        request = _make_request(evidences=[_make_evidence()])
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            request
        ]
        mock_db.query.return_value.filter.return_value.all.return_value = [(3, "Ana")]

        result = await repo.list_requests(1)

        assert result[0]["id"] == 1
        assert result[0]["evidences"][0]["uploader_name"] == "Ana"

    @pytest.mark.asyncio
    async def test_get_request_detail_found(self, repo, mock_db):
        """Test get_request_detail returns the enriched request."""

        request = _make_request()
        mock_db.query.return_value.filter.return_value.first.return_value = request

        result = await repo.get_request_detail(1, 1)

        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_get_request_detail_not_found(self, repo, mock_db):
        """Test get_request_detail returns None when the request does not exist."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = await repo.get_request_detail(1, 999)

        assert result is None

    @pytest.mark.asyncio
    async def test_create_request(self, repo, mock_db):
        """Test create_request persists and returns the enriched request."""

        data = ImprovementPlanEvidenceRequestCreate(title="Rúbrica")
        # `refresh` doesn't populate relationships on a MagicMock; give the
        # created row empty ones so `_enrich` can iterate them.
        added = []
        mock_db.add.side_effect = lambda obj: added.append(obj)

        def _refresh(obj):
            obj.comments = []
            obj.evidences = []

        mock_db.refresh.side_effect = _refresh

        result = await repo.create_request(1, data, requested_by=2)

        assert result["title"] == "Rúbrica"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_request_not_found(self, repo, mock_db):
        """Test update_request returns None when the request does not exist."""

        mock_db.query.return_value.filter.return_value.first.return_value = None
        data = ImprovementPlanEvidenceRequestUpdate(title="Nuevo")

        result = await repo.update_request(1, 999, data)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_request_applies_only_the_given_fields(self, repo, mock_db):
        """Test update_request only sets fields present in the payload."""

        request = _make_request()
        mock_db.query.return_value.filter.return_value.first.return_value = request
        data = ImprovementPlanEvidenceRequestUpdate(title="Nuevo título")

        result = await repo.update_request(1, 1, data)

        assert request.title == "Nuevo título"
        assert result["title"] == "Nuevo título"

    @pytest.mark.asyncio
    async def test_update_request_serializes_the_status_enum(self, repo, mock_db):
        """Test update_request converts a status enum to its string value."""

        request = _make_request()
        mock_db.query.return_value.filter.return_value.first.return_value = request
        data = ImprovementPlanEvidenceRequestUpdate(
            status=EvidenceRequestStatus.APROBADA
        )

        await repo.update_request(1, 1, data)

        assert request.status == "APROBADA"

    def test_set_request_status_updates_when_found(self, repo, mock_db):
        """Test set_request_status moves an existing request to a new state."""

        request = _make_request()
        mock_db.query.return_value.filter.return_value.first.return_value = request

        repo.set_request_status(1, "EN_REVISION")

        assert request.status == "EN_REVISION"
        mock_db.commit.assert_called_once()

    def test_set_request_status_noop_when_missing(self, repo, mock_db):
        """Test set_request_status does nothing when the request is missing."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        repo.set_request_status(999, "EN_REVISION")

        mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_comment_without_an_author(self, repo, mock_db):
        """Test add_comment skips the author lookup for a system message."""

        def _refresh(obj):
            obj.id = 1
            obj.created_at = None

        mock_db.refresh.side_effect = _refresh

        result = await repo.add_comment(1, "Reenviado", is_system=True)

        assert result["author_name"] is None
        assert result["is_system"] is True

    @pytest.mark.asyncio
    async def test_add_comment_with_an_author_looks_up_the_name(self, repo, mock_db):
        """Test add_comment resolves the author's display name."""

        def _refresh(obj):
            obj.id = 1
            obj.created_at = None

        mock_db.refresh.side_effect = _refresh
        mock_db.query.return_value.filter.return_value.first.return_value = ("Ana",)

        result = await repo.add_comment(1, "Listo", author_id=3)

        assert result["author_name"] == "Ana"

    def test_get_evidence_found(self, repo, mock_db):
        """Test get_evidence returns the matching evidence."""

        evidence = _make_evidence()
        mock_db.query.return_value.filter.return_value.first.return_value = evidence

        result = repo.get_evidence(1, 1)

        assert result == evidence

    @pytest.mark.asyncio
    async def test_add_evidence_strips_a_blank_description(self, repo, mock_db):
        """Test add_evidence stores None for a whitespace-only description."""

        def _refresh(obj):
            obj.id = 1
            obj.created_at = None

        mock_db.refresh.side_effect = _refresh

        result = await repo.add_evidence(1, "/tmp/e.pdf", description="   ")

        assert result["description"] is None

    @pytest.mark.asyncio
    async def test_add_evidence_keeps_a_real_description(self, repo, mock_db):
        """Test add_evidence keeps a non-blank description."""

        def _refresh(obj):
            obj.id = 1
            obj.created_at = None

        mock_db.refresh.side_effect = _refresh

        result = await repo.add_evidence(1, "/tmp/e.pdf", description="Rúbrica firmada")

        assert result["description"] == "Rúbrica firmada"

    @pytest.mark.asyncio
    async def test_review_evidence_not_found(self, repo, mock_db):
        """Test review_evidence returns None when the evidence does not exist."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = await repo.review_evidence(999, "APROBADA", reviewed_by=2)

        assert result is None

    @pytest.mark.asyncio
    async def test_review_evidence_records_the_verdict(self, repo, mock_db):
        """Test review_evidence sets the status and reviewer."""

        evidence = _make_evidence()
        mock_db.query.return_value.filter.return_value.first.return_value = evidence

        result = await repo.review_evidence(1, "APROBADA", reviewed_by=2)

        assert evidence.status == "APROBADA"
        assert evidence.reviewed_by == 2
        assert result["status"] == "APROBADA"

    @pytest.mark.asyncio
    async def test_delete_evidence_not_found(self, repo, mock_db):
        """Test delete_evidence returns None when the evidence does not exist."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = await repo.delete_evidence(1, 999)

        assert result is None
        mock_db.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_evidence_removes_the_row_and_returns_its_path(
        self, repo, mock_db
    ):
        """Test delete_evidence deletes the row and returns its file path."""

        evidence = _make_evidence()
        mock_db.query.return_value.filter.return_value.first.return_value = evidence

        result = await repo.delete_evidence(1, 1)

        assert result == "/tmp/e.pdf"
        mock_db.delete.assert_called_once_with(evidence)
        mock_db.commit.assert_called_once()
