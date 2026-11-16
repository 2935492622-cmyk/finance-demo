"""P1 unit/ASGI contract tests. No real MySQL rows are read or written."""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import make_transient_to_detached

from app import crud, database
from app.database import get_session
from app.exceptions import APIError
from app.main import create_app
from app.models import Transaction
from app.schemas import TransactionWrite
from test_http_contract import request
from test_validation import valid_payload


def existing_record():
    return Transaction(
        id=42, amount=Decimal("10.00"), type="income", category="原分类", note="原备注",
        transaction_date=date(2026, 11, 15), created_at=datetime(2026, 11, 15, 1),
        updated_at=datetime(2026, 11, 15, 2),
    )


@pytest.fixture
def app_and_session():
    app = create_app()
    session = MagicMock()
    app.dependency_overrides[get_session] = lambda: session
    return app, session


@pytest.mark.parametrize("method", ["PUT", "DELETE"])
@pytest.mark.parametrize("record_id", ["0", "-1", "4294967296", "1.0", "1.00", "1.2", "1e0", "+1", "abc", "%201", "1%20", "１２"])
def test_invalid_path_id_is_422_without_querying_db(app_and_session, method, record_id):
    app, session = app_and_session
    kwargs = {"json": valid_payload()} if method == "PUT" else {}
    response = request(app, method, f"/api/transactions/{record_id}", **kwargs)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"][0]["field"] == "path.id"
    session.get.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize("method", ["PUT", "DELETE"])
@pytest.mark.parametrize("record_id", ["1", "4294967295"])
def test_valid_missing_id_is_404(app_and_session, method, record_id):
    app, session = app_and_session
    session.get.return_value = None
    kwargs = {"json": valid_payload()} if method == "PUT" else {}
    response = request(app, method, f"/api/transactions/{record_id}", **kwargs)
    assert response.status_code == 404
    assert response.json()["error"] == {"code": "NOT_FOUND", "message": "收支记录不存在", "details": []}
    session.get.assert_called_once_with(Transaction, int(record_id), with_for_update=True)
    session.commit.assert_not_called()


def test_put_full_replacement_keeps_readonly_fields_and_clears_omitted_note(app_and_session):
    app, session = app_and_session
    record = existing_record()
    session.get.return_value = record
    payload = valid_payload(amount="3.20", type="expense", category="  新分类  ", transaction_date="2026-11-16")
    del payload["note"]
    response = request(app, "PUT", "/api/transactions/42", json=payload)
    assert response.status_code == 200
    result = response.json()
    assert result["id"] == 42
    assert result["created_at"] == "2026-11-15T01:00:00.000000Z"
    assert result["updated_at"] >= "2026-11-15T02:00:00.000000Z"
    assert result["amount"] == "3.20"
    assert result["type"] == "expense"
    assert result["category"] == "新分类"
    assert result["transaction_date"] == "2026-11-16"
    assert result["note"] == ""
    session.commit.assert_called_once()


@pytest.mark.parametrize("payload_change", ["missing_category", "zero_amount", "readonly_id"])
def test_put_invalid_payload_leaves_original_record_untouched(app_and_session, payload_change):
    app, session = app_and_session
    record = existing_record()
    session.get.return_value = record
    payload = valid_payload()
    if payload_change == "missing_category":
        del payload["category"]
    elif payload_change == "zero_amount":
        payload["amount"] = "0.00"
    else:
        payload["id"] = 7
    response = request(app, "PUT", "/api/transactions/42", json=payload)
    assert response.status_code == 422
    assert (record.amount, record.type, record.category, record.note) == (Decimal("10.00"), "income", "原分类", "原备注")
    session.get.assert_not_called()
    session.commit.assert_not_called()


def test_update_does_not_move_timestamp_backwards(monkeypatch):
    session = MagicMock()
    record = existing_record()
    session.get.return_value = record
    monkeypatch.setattr(crud, "utc_now", lambda: datetime(2026, 11, 14))
    updated = crud.update_transaction(session, 42, TransactionWrite.model_validate(valid_payload()))
    assert updated.created_at == datetime(2026, 11, 15, 1)
    assert updated.updated_at == datetime(2026, 11, 15, 2)
    session.commit.assert_called_once()


def test_kept_timestamp_is_marked_for_update_instead_of_using_onupdate_default(monkeypatch):
    session = MagicMock()
    record = existing_record()
    # Model a clean loaded ORM row: setting an equal value normally does not
    # make it dirty, so the column's onupdate default could otherwise win.
    make_transient_to_detached(record)
    session.get.return_value = record
    monkeypatch.setattr(crud, "utc_now", lambda: datetime(2026, 11, 14))
    updated = crud.update_transaction(session, 42, TransactionWrite.model_validate(valid_payload()))
    history = inspect(updated).attrs.updated_at.history
    assert history.has_changes()
    assert history.added == [datetime(2026, 11, 15, 2)]


def test_delete_success_has_no_json_body_and_repeated_delete_is_404(app_and_session):
    app, session = app_and_session
    record = existing_record()
    session.get.side_effect = [record, None]
    first = request(app, "DELETE", "/api/transactions/42")
    assert first.status_code == 204
    assert first.content == b""
    assert first.headers.get("content-type") is None
    session.delete.assert_called_once_with(record)
    session.commit.assert_called_once()
    second = request(app, "DELETE", "/api/transactions/42")
    assert second.status_code == 404
    assert second.json()["error"]["code"] == "NOT_FOUND"
    assert session.commit.call_count == 1


@pytest.mark.parametrize("method", ["PUT", "DELETE"])
def test_commit_failure_is_503_and_rolls_back_without_success(method, monkeypatch):
    app = create_app()
    session = MagicMock()
    session.get.return_value = existing_record()
    session.commit.side_effect = OperationalError("private SQL", {}, Exception("private DB secret"))
    # Keep the real request Session generator so its rollback/close handling is
    # covered while substituting only the connection/session factory.
    monkeypatch.setattr(database, "get_engine", lambda: object())
    monkeypatch.setattr(database, "sessionmaker", lambda **_kwargs: lambda: session)
    kwargs = {"json": valid_payload()} if method == "PUT" else {}
    response = request(app, method, "/api/transactions/42", **kwargs)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
    assert "private" not in response.text
    session.rollback.assert_called_once()
    session.close.assert_called_once()


@pytest.mark.parametrize("operation", ["update", "delete"])
def test_missing_record_does_not_attempt_mutation(operation):
    session = MagicMock()
    session.get.return_value = None
    with pytest.raises(APIError) as exc:
        if operation == "update":
            crud.update_transaction(session, 42, TransactionWrite.model_validate(valid_payload()))
        else:
            crud.delete_transaction(session, 42)
    assert exc.value.status == 404
    session.delete.assert_not_called()
    session.commit.assert_not_called()


def test_openapi_has_put_delete_and_integer_path_bounds(app_and_session):
    app, _session = app_and_session
    schema = request(app, "GET", "/openapi.json").json()
    path = schema["paths"]["/api/transactions/{id}"]
    assert {"put", "delete"}.issubset(path)
    for method in ["put", "delete"]:
        parameter = path[method]["parameters"][0]
        assert parameter["name"] == "id"
        assert parameter["schema"]["type"] == "integer"
        assert parameter["schema"]["minimum"] == 1
        assert parameter["schema"]["maximum"] == 4294967295
    assert "content" not in path["delete"]["responses"]["204"]
