import asyncio

import httpx
import pytest
from sqlalchemy.exc import OperationalError

from app.database import get_session
from app.main import create_app
from test_validation import valid_payload


@pytest.fixture
def app():
    return create_app()


def request(app, method, path, **kwargs):
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://unit-test"
        ) as client:
            return await client.request(method, path, **kwargs)
    return asyncio.run(run())


@pytest.mark.parametrize("path,field", [
    ("/api/transactions?type=Income", "query.type"),
    ("/api/summary?category=", "query.category"),
    ("/api/transactions?start_date=2026-02-30", "query.start_date"),
    ("/api/summary?end_date=0999-12-31", "query.end_date"),
    ("/api/transactions?start_date=2026-11-30&end_date=2026-11-01", "query.start_date"),
    ("/api/summary?unknown=1", "query.unknown"),
])
def test_query_errors_are_422_without_database(app, path, field):
    response = request(app, "GET", path)
    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "VALIDATION_ERROR"
    assert body["details"][0]["field"] == field
    assert set(body) == {"code", "message", "details"}


def test_amount_error_does_not_echo_input(app):
    secret_input = "private-value-not-to-echo"
    response = request(app, "POST", "/api/transactions", json=valid_payload(amount=secret_input))
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "body.amount"
    assert secret_input not in response.text


def test_malformed_json_has_body_location(app):
    response = request(app, "POST", "/api/transactions", content='{"bad-json"', headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "body"


@pytest.mark.parametrize("path", ["/api/health", "/api/transactions", "/api/summary"])
def test_database_exception_is_safe_503(app, path):
    class UnavailableSession:
        def execute(self, *_args, **_kwargs):
            raise OperationalError("SELECT sensitive_SQL", {}, Exception("sensitive-password"))
        scalars = execute

    app.dependency_overrides[get_session] = lambda: UnavailableSession()
    response = request(app, "GET", path)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert response.json()["error"]["details"] == []
    assert "sensitive" not in response.text


def test_unexpected_exception_is_safe_500(app):
    class BrokenSession:
        def execute(self, *_args, **_kwargs):
            raise RuntimeError("private-debug-information")
    app.dependency_overrides[get_session] = lambda: BrokenSession()
    response = request(app, "GET", "/api/health")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "private-debug-information" not in response.text


def test_openapi_describes_money_and_shared_filter_names(app):
    schema = request(app, "GET", "/openapi.json").json()
    assert schema["components"]["schemas"]["TransactionWrite"]["properties"]["amount"]["type"] == "string"
    for path in ["/api/transactions", "/api/summary"]:
        names = [item["name"] for item in schema["paths"][path]["get"]["parameters"]]
        assert names == ["type", "category", "start_date", "end_date"]
