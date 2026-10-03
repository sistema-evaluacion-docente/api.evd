"""Tests for the upload size guard."""

import pytest
from fastapi import HTTPException

from api.utils.file_validation import validate_file_size

MB = 1024 * 1024


class TestValidateFileSize:
    """validate_file_size"""

    def test_default_limit_accepts_a_20_mb_file(self, monkeypatch):
        """Test a file of exactly the configured limit passes."""

        monkeypatch.setattr("api.utils.file_validation.config.MAX_UPLOAD_SIZE_MB", 20)

        validate_file_size(b"\0" * (20 * MB))

    def test_default_limit_rejects_a_file_over_20_mb(self, monkeypatch):
        """Test one byte over the configured limit is a 400 in Spanish."""

        monkeypatch.setattr("api.utils.file_validation.config.MAX_UPLOAD_SIZE_MB", 20)

        with pytest.raises(HTTPException) as exc:
            validate_file_size(b"\0" * (20 * MB + 1))

        assert exc.value.status_code == 400
        assert "20MB" in exc.value.detail

    def test_explicit_limit_overrides_the_configured_one(self):
        """Test a caller-supplied limit wins over the configured default."""

        with pytest.raises(HTTPException):
            validate_file_size(b"\0" * (MB + 1), limit=1)
