"""Tests for the on-disk storage of improvement plan files."""

import os

import pytest

from api.utils import plan_files
from api.utils.plan_files import (
    PLANS_SUBDIR,
    delete_plan_file,
    delete_plan_files,
    plan_documents_dir,
    plan_evidences_dir,
    save_plan_document,
    save_plan_evidence,
)


@pytest.fixture
def uploads(tmp_path, monkeypatch):
    """An UPLOAD_DIR of our own, so nothing real is ever removed."""

    monkeypatch.setattr(plan_files.config, "UPLOAD_DIR", str(tmp_path))

    return tmp_path


def _plan_dir(uploads, plan_id: int):
    directory = uploads / PLANS_SUBDIR / str(plan_id)
    (directory / "documents").mkdir(parents=True)
    (directory / "documents" / "acta.pdf").write_bytes(b"%PDF-")
    (directory / "evidences").mkdir()
    (directory / "evidences" / "evidencia.pdf").write_bytes(b"%PDF-")

    return directory


class TestDeletePlanFiles:
    """Deleting the row cascades in the database, not on the filesystem."""

    def test_removes_everything_the_plan_stored(self, uploads):
        directory = _plan_dir(uploads, 7)

        delete_plan_files(7)

        assert not directory.exists()

    def test_leaves_other_plans_untouched(self, uploads):
        mine = _plan_dir(uploads, 7)
        theirs = _plan_dir(uploads, 8)

        delete_plan_files(7)

        assert not mine.exists()
        assert theirs.exists()

    def test_does_nothing_for_a_plan_that_stored_nothing(self, uploads):
        """Test a plan whose files were never created is not an error."""

        delete_plan_files(999)

    def test_never_steps_outside_the_uploads_directory(self, uploads):
        """Test the id is what builds the path, so it must not escape it."""

        outsider = uploads.parent / "no-tocar"
        outsider.mkdir()
        (outsider / "importante.txt").write_text("no")

        delete_plan_files(f"..{os.sep}..{os.sep}no-tocar")

        assert (outsider / "importante.txt").exists()


class TestSaveAndLocateFiles:
    """Saving a document/evidence and finding its directory back."""

    def test_plan_documents_dir(self, uploads):
        directory = plan_documents_dir(7)

        assert directory == str(uploads / PLANS_SUBDIR / "7" / "documents")

    def test_plan_evidences_dir(self, uploads):
        directory = plan_evidences_dir(7)

        assert directory == str(uploads / PLANS_SUBDIR / "7" / "evidences")

    def test_save_plan_document_writes_the_file_under_documents(self, uploads):
        filepath = save_plan_document(7, b"%PDF-1.4 acta", "formato-2")

        assert filepath.startswith(str(uploads / PLANS_SUBDIR / "7" / "documents"))
        assert os.path.basename(filepath).startswith("formato-2_")
        assert open(filepath, "rb").read() == b"%PDF-1.4 acta"

    def test_save_plan_evidence_writes_the_file_under_evidences(self, uploads):
        filepath = save_plan_evidence(7, b"%PDF-1.4 rubrica")

        assert filepath.startswith(str(uploads / PLANS_SUBDIR / "7" / "evidences"))
        assert os.path.basename(filepath).startswith("evidencia_")
        assert open(filepath, "rb").read() == b"%PDF-1.4 rubrica"


class TestDeletePlanFile:
    """Replacing a document/evidence drops the stale file, defensively."""

    def test_does_nothing_without_a_path(self, uploads):
        delete_plan_file(None)  # must not raise

    def test_removes_a_file_inside_the_uploads_directory(self, uploads):
        filepath = save_plan_document(7, b"%PDF-", "formato-1")

        delete_plan_file(filepath)

        assert not os.path.isfile(filepath)

    def test_does_nothing_for_a_missing_file(self, uploads):
        missing = str(uploads / PLANS_SUBDIR / "7" / "documents" / "gone.pdf")

        delete_plan_file(missing)  # must not raise

    def test_never_removes_a_file_outside_the_uploads_directory(
        self, uploads, tmp_path_factory
    ):
        outsider_dir = tmp_path_factory.mktemp("outside")
        outsider = outsider_dir / "importante.txt"
        outsider.write_text("no")

        delete_plan_file(str(outsider))

        assert outsider.exists()
