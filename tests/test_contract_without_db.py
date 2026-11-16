"""Independent P0 HTTP validation and real connection-refusal checks.

This uses the actual ASGI app, not a fake response or a SQLite database.
It does not prove successful MySQL CRUD or browser persistence.
"""

from pathlib import Path
import socket
import sys

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def app_with_unavailable_database(monkeypatch):
    try:
        from app.config import get_settings
        from app.database import get_engine
        from app.main import create_app
    except ImportError:
        pytest.skip("后端尚未提供 P0 模块，独立校验测试受阻")
    # Keep an unused TCP port bound but not listening: no real DB can own it.
    with socket.socket() as closed_endpoint:
        closed_endpoint.bind(("127.0.0.1", 0))
        for name, value in {
            "DB_HOST": "127.0.0.1", "DB_PORT": str(closed_endpoint.getsockname()[1]),
            "DB_NAME": "finance_demo", "DB_USER": "qa_invalid_user",
            "DB_PASSWORD": "qa_nonsecret_failure_sentinel",
        }.items():
            monkeypatch.setenv(name, value)
        if get_engine.cache_info().currsize:
            get_engine().dispose()
        get_engine.cache_clear()
        get_settings.cache_clear()
        try:
            yield create_app()
        finally:
            if get_engine.cache_info().currsize:
                get_engine().dispose()
            get_engine.cache_clear()
            get_settings.cache_clear()


def payload(**changes):
    result = {"amount": "12.30", "type": "expense", "category": "餐饮", "note": "", "transaction_date": "2026-11-15"}
    result.update(changes)
    return result


def assert_422(response, field):
    assert response.status_code == 422
    error = response.json()["error"]
    assert set(error) == {"code", "message", "details"}
    assert error["code"] == "VALIDATION_ERROR"
    assert field in [item["field"] for item in error["details"]]
    assert all(set(item) == {"field", "message"} for item in error["details"])
    assert "qa_nonsecret_failure_sentinel" not in response.text


@pytest.mark.anyio
@pytest.mark.parametrize("changes,field", [
    ({"amount": "0.00"}, "body.amount"), ({"amount": "-1.00"}, "body.amount"),
    ({"amount": 1.2}, "body.amount"), ({"amount": True}, "body.amount"),
    ({"amount": "1.001"}, "body.amount"), ({"amount": "01.00"}, "body.amount"),
    ({"type": "Income"}, "body.type"), ({"type": "income "}, "body.type"),
    ({"category": "\u3000\t"}, "body.category"), ({"category": "😀" * 51}, "body.category"),
    ({"note": None}, "body.note"), ({"note": "字" * 501}, "body.note"),
    ({"transaction_date": "2026-02-30"}, "body.transaction_date"),
    ({"transaction_date": "0999-12-31"}, "body.transaction_date"),
    ({"transaction_date": "2026-11-15T00:00:00Z"}, "body.transaction_date"),
    ({"id": 1}, "body.id"),
])
async def test_invalid_body_precedes_database_access(app_with_unavailable_database, changes, field):
    transport = httpx.ASGITransport(app=app_with_unavailable_database)
    async with httpx.AsyncClient(transport=transport, base_url="http://qa.local") as client:
        assert_422(await client.post("/api/transactions", json=payload(**changes)), field)


@pytest.mark.anyio
@pytest.mark.parametrize("params,field", [
    ({"type": ""}, "query.type"), ({"category": ""}, "query.category"),
    ({"start_date": ""}, "query.start_date"), ({"end_date": "2026-02-30"}, "query.end_date"),
    ({"start_date": "2026-11-16", "end_date": "2026-11-15"}, "query.start_date"),
    ({"page": "1"}, "query.page"),
])
async def test_query_validation_shared_by_endpoints(app_with_unavailable_database, params, field):
    transport = httpx.ASGITransport(app=app_with_unavailable_database)
    async with httpx.AsyncClient(transport=transport, base_url="http://qa.local") as client:
        for endpoint in ["transactions", "summary"]:
            assert_422(await client.get(f"/api/{endpoint}", params=params), field)


@pytest.mark.anyio
async def test_malformed_json_safe_error(app_with_unavailable_database):
    transport = httpx.ASGITransport(app=app_with_unavailable_database)
    async with httpx.AsyncClient(transport=transport, base_url="http://qa.local") as client:
        response = await client.post("/api/transactions", content='{"amount":', headers={"Content-Type": "application/json"})
        assert_422(response, "body")


@pytest.mark.anyio
async def test_real_connection_refusal_is_503(app_with_unavailable_database):
    transport = httpx.ASGITransport(app=app_with_unavailable_database)
    async with httpx.AsyncClient(transport=transport, base_url="http://qa.local") as client:
        responses = [await client.get(f"/api/{endpoint}") for endpoint in ["health", "transactions", "summary"]]
        responses.append(await client.post("/api/transactions", json=payload()))
    for response in responses:
        assert response.status_code == 503
        assert response.json() == {"error": {
            "code": "DATABASE_UNAVAILABLE",
            "message": response.json()["error"]["message"],
            "details": [],
        }}
        assert response.json()["error"]["message"]
        assert "qa_invalid_user" not in response.text
        assert "qa_nonsecret_failure_sentinel" not in response.text
        assert "SELECT " not in response.text
        assert "INSERT " not in response.text
