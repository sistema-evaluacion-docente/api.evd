"""Utilities for validating uploaded files."""

from fastapi import HTTPException

from api.config import config


def validate_file_size(file_bytes: bytes, limit: int | None = None) -> None:
    """Validate that the file does not exceed the configured maximum size.

    Reads the length of the provided byte string and compares it against
    ``config.MAX_UPLOAD_SIZE_MB``. If the file is larger, an ``HTTPException``
    with status code 400 is raised.

    Args:
        file_bytes: Raw content of the uploaded file.
        limit: Maximum allowed file size in MB.

    Raises:
        HTTPException: If the file size exceeds the configured limit.
    """

    if limit is None:
        limit = config.MAX_UPLOAD_SIZE_MB

    max_size = limit * 1024 * 1024

    if len(file_bytes) > max_size:
        raise HTTPException(
            status_code=400,
            detail=(f"El archivo excede el tamaño máximo de " f"{limit}MB"),
        )
