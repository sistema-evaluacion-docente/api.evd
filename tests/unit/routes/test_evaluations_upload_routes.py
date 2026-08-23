"""
Tests for the evaluation upload route.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.controllers.evaluations import get_evaluations_controller
from api.exceptions import PermissionDeniedError
from api.routes.evaluations import router
from tests.unit.routes.conftest import DIRECTOR_USER, DOCENTE_USER

PDF = ("presencial.pdf", b"%PDF-1.4 fake", "application/pdf")


@pytest.fixture
def controller():
    """Mock EvaluationsController."""

    mock = MagicMock()
    mock.prepare_upload = AsyncMock()
    return mock


@pytest.fixture
def client(make_client, controller, auth):
    """Test client for the evaluations router, authenticated as a director."""

    auth.as_user(DIRECTOR_USER)
    return make_client(router, {get_evaluations_controller: controller})


class TestUploadEvaluation:
    """Test suite for POST /evaluations/upload."""

    async def test_rejects_a_pdf_of_another_department(self, client, controller):
        """The department mismatch raised by the service becomes a 403 envelope."""

        controller.prepare_upload.side_effect = PermissionDeniedError(
            "El PDF corresponde al departamento SISTEMAS (52), que no es el "
            "departamento asignado a usted; solo puede subir las evaluaciones "
            "de su propio departamento"
        )

        response = client.post("/evaluations/upload", files={"file": PDF})

        assert response.status_code == 403
        error = response.json()["error"]
        assert error["code"] == "PERMISSION_DENIED"
        assert "SISTEMAS (52)" in error["message"]

    async def test_accepts_a_pdf_of_the_own_department(self, client, controller):
        """A matching department is accepted and the parsing is scheduled."""

        controller.prepare_upload.return_value = ({"id": 1}, {"teachers": []})

        with patch("api.routes.evaluations.process_evaluation") as process:
            response = client.post("/evaluations/upload", files={"file": PDF})

        assert response.status_code == 202
        assert response.json()["data"] == {"id": 1}
        process.assert_called_once_with(1, {"teachers": []})

    async def test_forwards_the_uploaded_file_and_the_director(
        self, client, controller
    ):
        """The service authorizes the upload against the acting director."""

        controller.prepare_upload.return_value = ({"id": 1}, {})

        with patch("api.routes.evaluations.process_evaluation"):
            client.post("/evaluations/upload", files={"file": PDF})

        kwargs = controller.prepare_upload.call_args.kwargs
        assert kwargs["current_user"]["department_id"] == DIRECTOR_USER["department_id"]
        assert [(u.filename, u.content) for u in kwargs["uploads"]] == [
            (PDF[0], PDF[1])
        ]

    async def test_requires_a_file(self, client, controller):
        """The `file` part is mandatory."""

        response = client.post("/evaluations/upload")

        assert response.status_code == 422
        controller.prepare_upload.assert_not_called()

    async def test_docente_is_forbidden(self, client, controller, auth):
        """Only ADMIN and DIRECTOR may upload an evaluation."""

        auth.as_user(DOCENTE_USER)

        response = client.post("/evaluations/upload", files={"file": PDF})

        assert response.status_code == 403
        controller.prepare_upload.assert_not_called()
