"""
Tests for ResponseEnvelopeMiddleware.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.core.middleware import ResponseEnvelopeMiddleware, extract_pagination


class TestResponseEnvelopeMiddleware:
    """Test suite for ResponseEnvelopeMiddleware."""

    @pytest.fixture
    def app(self):
        """Create test app with middleware."""

        test_app = FastAPI()
        test_app.add_middleware(ResponseEnvelopeMiddleware)

        @test_app.get("/success")
        def success():
            return {"message": "ok"}

        @test_app.get("/paginated")
        def paginated():
            return {
                "items": [{"id": 1}, {"id": 2}],
                "total": 10,
                "page": 1,
                "limit": 2,
                "pages": 5,
            }

        @test_app.get("/partial-pagination")
        def partial_pagination():
            return {
                "items": [{"id": 1}],
                "total": 10,
            }

        @test_app.get("/error")
        def error():
            from fastapi import HTTPException

            raise HTTPException(status_code=400, detail="Bad request")

        @test_app.get("/html")
        def html():
            from fastapi.responses import HTMLResponse

            return HTMLResponse("<html></html>")

        return test_app

    @pytest.fixture
    def client(self, app):
        """Create test client."""

        return TestClient(app)

    def test_success_response_enveloped(self, client):
        """Test successful JSON response is wrapped in envelope."""

        response = client.get("/success")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["data"] == {"message": "ok"}
        assert data["pagination"] is None
        assert data["error"] is None
        assert "timestamp" in data

    def test_paginated_response(self, client):
        """Test paginated response extracts pagination metadata."""

        response = client.get("/paginated")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["data"] == [{"id": 1}, {"id": 2}]
        assert data["pagination"] == {
            "total": 10,
            "page": 1,
            "limit": 2,
            "pages": 5,
        }
        assert data["error"] is None

    def test_partial_pagination_not_extracted(self, client):
        """Test response with partial pagination keys is not treated as paginated."""

        response = client.get("/partial-pagination")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["data"] == {"items": [{"id": 1}], "total": 10}
        assert data["pagination"] is None

    def test_error_response_not_enveloped(self, client):
        """Test error responses (status >= 400) are not wrapped."""

        response = client.get("/error")

        assert response.status_code == 400
        data = response.json()

        # Error responses are handled by exception handlers, not middleware
        assert "detail" in data or "error" in data

    def test_html_response_not_enveloped(self, client):
        """Test non-JSON responses are not wrapped."""

        response = client.get("/html")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert response.text == "<html></html>"

    def test_docs_excluded(self, client):
        """Test /docs is excluded from envelope."""

        response = client.get("/docs")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")

    def test_openapi_excluded(self, client):
        """Test /openapi.json is excluded from envelope."""

        response = client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()

        # Should be OpenAPI spec, not envelope
        assert "openapi" in data
        assert "info" in data
        assert "status" not in data or data.get("status") != "success"


class TestExtractPagination:
    """Test suite for extract_pagination helper."""

    def test_non_dict_returns_as_is(self):
        """Test non-dict body returns as-is with no pagination."""

        data, pagination = extract_pagination([1, 2, 3])
        assert data == [1, 2, 3]
        assert pagination is None

    def test_dict_without_pagination_keys(self):
        """Test dict without pagination keys returns as-is."""

        body = {"message": "ok", "data": "test"}
        data, pagination = extract_pagination(body)
        assert data == body
        assert pagination is None

    def test_dict_with_all_pagination_keys_and_items(self):
        """Test dict with all pagination keys extracts pagination and items."""

        body = {
            "items": [{"id": 1}, {"id": 2}],
            "total": 10,
            "page": 1,
            "limit": 2,
            "pages": 5,
        }
        data, pagination = extract_pagination(body)

        assert data == [{"id": 1}, {"id": 2}]
        assert pagination == {
            "total": 10,
            "page": 1,
            "limit": 2,
            "pages": 5,
        }

    def test_dict_with_pagination_keys_no_items(self):
        """Test dict with pagination keys but no items key."""

        body = {
            "total": 10,
            "page": 1,
            "limit": 2,
            "pages": 5,
        }
        data, pagination = extract_pagination(body)

        assert data is None
        assert pagination == {
            "total": 10,
            "page": 1,
            "limit": 2,
            "pages": 5,
        }

    def test_dict_with_pagination_and_extra_keys(self):
        """Test dict with pagination and extra keys returns remaining as data."""

        body = {
            "items": [{"id": 1}],
            "total": 10,
            "page": 1,
            "limit": 2,
            "pages": 5,
            "extra": "value",
        }
        data, pagination = extract_pagination(body)

        assert data == {"items": [{"id": 1}], "extra": "value"}
        assert pagination == {
            "total": 10,
            "page": 1,
            "limit": 2,
            "pages": 5,
        }

    def test_dict_with_partial_pagination_keys(self):
        """Test dict with only some pagination keys is not treated as paginated."""

        body = {
            "items": [{"id": 1}],
            "total": 10,
            "page": 1,
        }
        data, pagination = extract_pagination(body)

        assert data == body
        assert pagination is None
