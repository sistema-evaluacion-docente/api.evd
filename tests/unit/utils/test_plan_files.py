"""Tests for the on-disk storage of improvement plan files."""

import os

import pytest

from api.utils import plan_files
from api.utils.plan_files import PLANS_SUBDIR, delete_plan_files


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
