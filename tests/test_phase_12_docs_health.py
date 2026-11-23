from fastapi.testclient import TestClient


def test_health_check_endpoint(client: TestClient):
    """Healthcheck endpoint /health returns 200 OK and status ok."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_openapi_json_schema(client: TestClient):
    """OpenAPI schema /openapi.json contains title, version, BearerAuth, and error responses."""
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    data = resp.json()

    # 1. API Metadata
    assert data["info"]["title"] == "TaskHub API"
    assert data["info"]["version"] == "1.0.0"
    assert "description" in data["info"]

    # 2. Security schemes in components
    components = data.get("components", {})
    security_schemes = components.get("securitySchemes", {})
    assert "BearerAuth" in security_schemes
    assert security_schemes["BearerAuth"]["type"] == "http"
    assert security_schemes["BearerAuth"]["scheme"] == "bearer"

    # 3. Documented error responses (401, 403, 404, 422) on protected endpoints
    paths = data.get("paths", {})
    assert "/api/v1/users/me" in paths
    user_me_patch = paths["/api/v1/users/me"]["patch"]
    responses = user_me_patch.get("responses", {})
    assert "401" in responses
    assert "403" in responses
    assert "404" in responses
    assert "422" in responses


def test_swagger_ui_docs(client: TestClient):
    """Swagger UI /docs returns 200 OK and serves Swagger HTML."""
    resp = client.get("/docs")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "swagger" in resp.text.lower()


def test_redoc_ui(client: TestClient):
    """ReDoc /redoc returns 200 OK and serves ReDoc HTML."""
    resp = client.get("/redoc")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "redoc" in resp.text.lower()
