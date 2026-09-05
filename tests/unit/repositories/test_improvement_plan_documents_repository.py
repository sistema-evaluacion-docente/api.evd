"""Tests for ImprovementPlanDocumentsRepository layer."""

from unittest.mock import MagicMock

import pytest

from api.models.improvement_plan_document import ImprovementPlanDocumentModel
from api.repositories.base import BaseRepository
from api.repositories.improvement_plan_documents import (
    ImprovementPlanDocumentsRepository,
)


class TestImprovementPlanDocumentsRepository:
    """Test suite for ImprovementPlanDocumentsRepository."""

    @pytest.fixture
    def repo(self, mock_db):
        """Create repository instance with mocked DB."""

        return ImprovementPlanDocumentsRepository(mock_db)

    @pytest.fixture
    def mock_document(self):
        """Mock ImprovementPlanDocumentModel instance."""

        doc = MagicMock(spec=ImprovementPlanDocumentModel)
        doc.id = 1
        doc.plan_id = 1
        doc.format_type = "formato-1"
        doc.generated_pdf_url = None
        doc.signed_pdf_url = None
        doc.signed_filename = None
        return doc

    def test_inherits_base_repository(self, repo):
        """Test ImprovementPlanDocumentsRepository inherits from BaseRepository."""

        assert isinstance(repo, BaseRepository)

    def test_get_by_format_found(self, repo, mock_db, mock_document):
        """Test get_by_format returns the matching document."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_document
        )

        result = repo.get_by_format(1, "formato-1")

        assert result == mock_document

    def test_get_by_format_not_found(self, repo, mock_db):
        """Test get_by_format returns None when there is no document row yet."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = repo.get_by_format(1, "formato-1")

        assert result is None

    def test_list_by_plan(self, repo, mock_db, mock_document):
        """Test list_by_plan returns every document attached to a plan."""

        mock_db.query.return_value.filter.return_value.all.return_value = [
            mock_document
        ]

        result = repo.list_by_plan(1)

        assert result == [mock_document]

    def test_set_generated_creates_a_new_row(self, repo, mock_db):
        """Test set_generated creates the row when it does not exist yet."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        document, previous = repo.set_generated(1, "formato-1", "/tmp/f.pdf", 2)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert previous is None
        assert document.generated_pdf_url == "/tmp/f.pdf"
        assert document.generated_by == 2

    def test_set_generated_reuses_the_existing_row_and_returns_the_stale_path(
        self, repo, mock_db, mock_document
    ):
        """Test set_generated overwrites an existing row and returns the old path."""

        mock_document.generated_pdf_url = "/tmp/old.pdf"
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_document
        )

        document, previous = repo.set_generated(1, "formato-1", "/tmp/new.pdf", 2)

        mock_db.add.assert_not_called()
        assert previous == "/tmp/old.pdf"
        assert document.generated_pdf_url == "/tmp/new.pdf"

    def test_set_signed_creates_a_new_row(self, repo, mock_db):
        """Test set_signed creates the row when it does not exist yet."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        document, previous = repo.set_signed(
            1, "formato-1", "/tmp/s.pdf", 2, filename="acta.pdf"
        )

        mock_db.add.assert_called_once()
        assert previous is None
        assert document.signed_pdf_url == "/tmp/s.pdf"
        assert document.signed_filename == "acta.pdf"

    def test_set_signed_reuses_the_existing_row_and_returns_the_stale_path(
        self, repo, mock_db, mock_document
    ):
        """Test set_signed overwrites an existing row and returns the old path."""

        mock_document.signed_pdf_url = "/tmp/old-signed.pdf"
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_document
        )

        document, previous = repo.set_signed(1, "formato-1", "/tmp/new-signed.pdf", 2)

        assert previous == "/tmp/old-signed.pdf"
        assert document.signed_pdf_url == "/tmp/new-signed.pdf"

    def test_clear_signed_without_a_document_row_returns_none(self, repo, mock_db):
        """Test clear_signed no-ops when there is no document row at all."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = repo.clear_signed(1, "formato-1")

        assert result is None
        mock_db.commit.assert_not_called()

    def test_clear_signed_without_a_signed_copy_returns_none(
        self, repo, mock_db, mock_document
    ):
        """Test clear_signed no-ops when the row has no signed copy yet."""

        mock_document.signed_pdf_url = None
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_document
        )

        result = repo.clear_signed(1, "formato-1")

        assert result is None
        mock_db.commit.assert_not_called()

    def test_clear_signed_drops_the_signed_copy(self, repo, mock_db, mock_document):
        """Test clear_signed clears the signed fields and returns the old path."""

        mock_document.signed_pdf_url = "/tmp/old-signed.pdf"
        mock_document.signed_filename = "acta.pdf"
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_document
        )

        result = repo.clear_signed(1, "formato-1")

        assert result == "/tmp/old-signed.pdf"
        assert mock_document.signed_pdf_url is None
        assert mock_document.signed_filename is None
        mock_db.commit.assert_called_once()
