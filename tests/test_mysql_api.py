"""P0 acceptance against a running FastAPI process and real finance_demo MySQL."""

from datetime import date
from decimal import Decimal
import re

import httpx
import pytest


def assert_validation(response, expected_field=None):
    assert response.status_code == 422
    error = response.json()["error"]
    assert set(error) == {"code", "message", "details"}
    assert error["code"] == "VALIDATION_ERROR"
    assert isinstance(error["message"], str) and error["message"]
    assert isinstance(error["details"], list)
    for detail in error["details"]:
        assert set(detail) == {"field", "message"}
    if expected_field:
        assert expected_field in [detail["field"] for detail in error["details"]]


def test_create_sql_summary_and_reconnect(live_ledger):
    ledger = live_ledger
    assert ledger.rows() == []
    created = []
    for amount, kind in [("1000.00", "income"), ("125.50", "expense")]:
        response = ledger.post(ledger.payload(amount=amount, type=kind))
        assert response.status_code == 201
        item = response.json()
        assert item["amount"] == amount
        assert item["type"] == kind
        assert item["created_at"] == item["updated_at"]
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z", item["created_at"])
        created.append(item)

    sql_rows = ledger.rows()
    assert [row["id"] for row in sql_rows] == [item["id"] for item in reversed(created)]
    assert [row["amount"] for row in sql_rows] == [Decimal("125.50"), Decimal("1000.00")]
    assert all(row["transaction_date"] == date(2026, 11, 15) for row in sql_rows)
    params = {"category": ledger.category}
    result = ledger.client.get("transactions", params=params)
    assert result.status_code == 200
    assert result.json() == {"items": list(reversed(created)), "total": 2}
    summary = ledger.client.get("summary", params=params)
    assert summary.status_code == 200
    assert summary.json() == {
        "total_income": "1000.00", "total_expense": "125.50", "balance": "874.50",
        "transaction_count": 2,
        "expense_by_category": [{"category": ledger.category, "amount": "125.50"}],
    }
    # A fresh HTTP client proves data is not tied to a single HTTP client instance.
    # Browser refresh and backend-restart persistence still require separate E2E evidence.
    with httpx.Client(base_url=ledger.client.base_url, timeout=10) as fresh:
        assert fresh.get("transactions", params=params).json() == result.json()


@pytest.mark.parametrize("amount", ["0.01", "99999999.99"])
def test_valid_amount_boundaries(live_ledger, amount):
    response = live_ledger.post(live_ledger.payload(amount=amount))
    assert response.status_code == 201
    assert response.json()["amount"] == amount
    assert live_ledger.rows()[0]["amount"] == Decimal(amount)


@pytest.mark.parametrize("amount", [
    "-1.00", "0.00", "100000000.00", "1.001", "1", "01.00", "1e2",
    "NaN", "Infinity", " 1.00", "+1.00", 1.25, 1, True, None,
])
def test_invalid_amount_does_not_write(live_ledger, amount):
    response = live_ledger.post(live_ledger.payload(amount=amount))
    assert_validation(response, "body.amount")
    assert live_ledger.rows() == []


@pytest.mark.parametrize("kind", ["Income", "income ", "other", "", None])
def test_invalid_type_does_not_write(live_ledger, kind):
    assert_validation(live_ledger.post(live_ledger.payload(type=kind)), "body.type")
    assert live_ledger.rows() == []


@pytest.mark.parametrize("day", ["2026-02-30", "0999-12-31", "", "2026-11-15T00:00:00Z", None])
def test_invalid_date_does_not_write(live_ledger, day):
    assert_validation(live_ledger.post(live_ledger.payload(transaction_date=day)), "body.transaction_date")
    assert live_ledger.rows() == []


def test_unicode_lengths_trim_and_optional_note(live_ledger):
    ledger = live_ledger
    category = ledger.tag + "餐" * (50 - len(ledger.tag))
    note = ledger.tag + "记" * (500 - len(ledger.tag))
    good = ledger.post(ledger.payload(category=f"\u3000{category} ", note=f" {note}\t"))
    assert good.status_code == 201
    assert good.json()["category"] == category
    assert good.json()["note"] == note
    assert ledger.rows(category)[0]["note"] == note
    assert_validation(ledger.post(ledger.payload(category="餐" * 51)), "body.category")
    assert_validation(ledger.post(ledger.payload(category="\u3000 \t")), "body.category")
    assert_validation(ledger.post(ledger.payload(note="记" * 501)), "body.note")
    payload = ledger.payload()
    del payload["note"]
    optional = ledger.post(payload)
    assert optional.status_code == 201
    assert optional.json()["note"] == ""


def test_unknown_missing_readonly_and_broken_json(live_ledger):
    ledger = live_ledger
    for field in ["amount", "type", "category", "transaction_date"]:
        payload = ledger.payload()
        del payload[field]
        assert_validation(ledger.post(payload), f"body.{field}")
    for field, value in [("id", 1), ("created_at", "2026-11-15T00:00:00Z"), ("unexpected", "x")]:
        assert_validation(ledger.post(ledger.payload(**{field: value})))
    assert_validation(ledger.client.post("transactions", content='{"amount":', headers={"Content-Type": "application/json"}))
    assert ledger.rows() == []


def test_empty_summary(live_ledger):
    params = {"category": live_ledger.category}
    assert live_ledger.client.get("transactions", params=params).json() == {"items": [], "total": 0}
    assert live_ledger.client.get("summary", params=params).json() == {
        "total_income": "0.00", "total_expense": "0.00", "balance": "0.00",
        "transaction_count": 0, "expense_by_category": [],
    }


def test_decimal_precision_and_negative_balance(live_ledger):
    for amount, kind in [("0.10", "income"), ("0.20", "income"), ("1.00", "expense")]:
        assert live_ledger.post(live_ledger.payload(amount=amount, type=kind)).status_code == 201
    summary = live_ledger.client.get("summary", params={"category": live_ledger.category}).json()
    assert summary["total_income"] == "0.30"
    assert summary["total_expense"] == "1.00"
    assert summary["balance"] == "-0.70"


def test_aggregate_exceeds_single_amount_limit(live_ledger):
    for _ in range(2):
        assert live_ledger.post(live_ledger.payload(amount="99999999.99", type="income")).status_code == 201
    summary = live_ledger.client.get("summary", params={"category": live_ledger.category}).json()
    assert summary["total_income"] == "199999999.98"
    assert summary["balance"] == "199999999.98"


def test_shared_filter_conditions_and_order(live_ledger):
    ledger = live_ledger
    for day, kind in [("2026-11-14", "expense"), ("2026-11-15", "income"), ("2026-11-16", "expense")]:
        assert ledger.post(ledger.payload(transaction_date=day, type=kind)).status_code == 201
    params = {"category": ledger.category, "start_date": "2026-11-15", "end_date": "2026-11-16"}
    listed = ledger.client.get("transactions", params=params).json()
    assert [row["transaction_date"] for row in listed["items"]] == ["2026-11-16", "2026-11-15"]
    assert listed["total"] == 2
    summary = ledger.client.get("summary", params=params).json()
    assert summary["transaction_count"] == 2
    assert summary["total_income"] == summary["total_expense"] == "12.30"
    params["type"] = "income"
    assert ledger.client.get("transactions", params=params).json()["total"] == 1
    summary = ledger.client.get("summary", params=params).json()
    assert summary["total_expense"] == "0.00"
    assert summary["expense_by_category"] == []


@pytest.mark.parametrize("params,field", [
    ({"start_date": "2026-11-16", "end_date": "2026-11-15"}, "query.start_date"),
    ({"type": ""}, "query.type"), ({"category": ""}, "query.category"),
    ({"start_date": ""}, "query.start_date"), ({"page": "1"}, "query.page"),
])
def test_invalid_query_shared_by_list_and_summary(live_ledger, params, field):
    for endpoint in ["transactions", "summary"]:
        assert_validation(live_ledger.client.get(endpoint, params=params), field)
