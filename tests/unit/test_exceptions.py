"""
Tests for exception handlers.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.exceptions import AppException
from api.exceptions.handlers import (
    app_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    generic_exception_handler,
)
from api.config import config


class TestExceptionHandlers:
    """Test suite for exception handlers."""

    @pytest.fixture
    def app(self):
        """Create test app with exception handlers."""

        test_app = FastAPI()

        test_app.add_exception_handler(AppException, app_exception_handler)
        test_app.add_exception_handler(
            RequestValidationError, validation_exception_handler
        )
        test_app.add_exception_handler(StarletteHTTPException, http_exception_handler)
        test_app.add_exception_handler(Exception, generic_exception_handler)

        @test_app.get("/app-error")
        def app_error():
            raise AppException(
                code="TEST_ERROR",
                message="Test error message",
                status_code=400,
            )

        @test_app.get("/http-error")
        def http_error():
            raise StarletteHTTPException(status_code=404, detail="Not found")

        @test_app.get("/generic-error")
        def generic_error():
            raise RuntimeError("Something went wrong")

        @test_app.post("/validation-error")
        def validation_error(data: dict):
            return data

        return test_app

    @pytest.fixture
    def client(self, app):
        """Create test client."""

        return TestClient(app, raise_server_exceptions=False)

    def test_app_exception_handler(self, client):
        """Test AppException is handled correctly."""

        response = client.get("/app-error")

        assert response.status_code == 400
        data = response.json()

        assert data["status"] == "error"
        assert data["data"] is None
        assert data["pagination"] is None
        assert data["error"]["code"] == "TEST_ERROR"
        assert data["error"]["message"] == "Test error message"
        assert "timestamp" in data

    def test_http_exception_handler(self, client):
        """Test HTTPException is handled correctly."""

        response = client.get("/http-error")

        assert response.status_code == 404
        data = response.json()

        assert data["status"] == "error"
        assert data["data"] is None
        assert data["pagination"] is None
        assert data["error"]["code"] == "HTTP_ERROR"
        assert data["error"]["message"] == "Not found"
        assert "timestamp" in data

    def test_generic_exception_handler_debug_false(self, client):
        """Test generic exception handler in production mode."""

        original_debug = config.DEBUG
        config.DEBUG = False

        try:
            response = client.get("/generic-error")

            assert response.status_code == 500
            data = response.json()

            assert data["status"] == "error"
            assert data["data"] is None
            assert data["pagination"] is None
            assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
            assert data["error"]["message"] == "An internal error occurred"
            assert "timestamp" in data
        finally:
            config.DEBUG = original_debug

    def test_generic_exception_handler_debug_true(self, client):
        """Test generic exception handler in debug mode."""

        original_debug = config.DEBUG
        config.DEBUG = True

        try:
            response = client.get("/generic-error")

            assert response.status_code == 500
            data = response.json()

            assert data["status"] == "error"
            assert data["data"] is None
            assert data["pagination"] is None
            assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
            assert data["error"]["message"] == "Something went wrong"
            assert data["error"]["details"]["type"] == "RuntimeError"
            assert "timestamp" in data
        finally:
            config.DEBUG = original_debug

    def test_validation_exception_handler(self, client):
        """Test RequestValidationError is handled correctly."""

        response = client.post("/validation-error", json="invalid")

        assert response.status_code == 422
        data = response.json()

        assert data["status"] == "error"
        assert data["data"] is None
        assert data["pagination"] is None
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert data["error"]["message"] == "Request validation failed"
        assert "details" in data["error"]
        assert "errors" in data["error"]["details"]
        assert "timestamp" in data
