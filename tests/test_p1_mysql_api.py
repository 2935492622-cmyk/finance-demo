"""P1 real HTTP/MySQL tests, after the main Agent reloads P1 routes."""

from datetime import date, datetime
from decimal import Decimal

import pytest


def sql_record(ledger, record_id):
    with ledger.connection.cursor() as cursor:
        cursor.execute("SELECT * FROM transactions WHERE id=%s", (record_id,))
        return cursor.fetchone()


def create_owned(ledger, **changes):
    response = ledger.post(ledger.payload(**changes))
    assert response.status_code == 201
    return response.json()


def assert_error(response, status, code, field=None):
    assert response.status_code == status
    error = response.json()["error"]
    assert set(error) == {"code", "message", "details"}
    assert error["code"] == code
    assert isinstance(error["message"], str) and error["message"]
    assert isinstance(error["details"], list)
    if field:
        assert field in [item["field"] for item in error["details"]]


def test_put_full_replace_sql_and_clear_omitted_note(live_ledger):
    ledger = live_ledger
    before = create_owned(ledger)
    new_category = ledger.category + "-edit"
    changed = ledger.payload(amount="45.67", type="income", category=new_category,
                             transaction_date="2024-02-29", note=ledger.tag + "-edited")
    response = ledger.put(before["id"], changed)
    assert response.status_code == 200
    after = response.json()
    assert after["id"] == before["id"]
    assert after["created_at"] == before["created_at"]
    assert after["updated_at"] >= before["updated_at"]
    for key, value in changed.items():
        assert after[key] == value
    stored = sql_record(ledger, before["id"])
    assert stored["amount"] == Decimal("45.67")
    assert stored["type"] == "income"
    assert stored["category"] == new_category
    assert stored["note"] == changed["note"]
    assert stored["transaction_date"] == date(2024, 2, 29)
    assert ledger.client.get("transactions", params={"category": ledger.category}).json()["total"] == 0
    summary = ledger.client.get("summary", params={"category": new_category}).json()
    assert summary["total_income"] == "45.67"
    assert summary["total_expense"] == "0.00"
    assert summary["balance"] == "45.67"
    del changed["note"]
    cleared = ledger.put(before["id"], changed)
    assert cleared.status_code == 200
    assert cleared.json()["note"] == ""
    assert cleared.json()["created_at"] == before["created_at"]
    assert sql_record(ledger, before["id"])["note"] == ""


def test_put_does_not_reverse_future_updated_timestamp(live_ledger):
    ledger = live_ledger
    original = create_owned(ledger)
    future = datetime(2099, 1, 1, 0, 0, 0, 123456)
    with ledger.connection.cursor() as cursor:
        cursor.execute("UPDATE transactions SET updated_at=%s WHERE id=%s", (future, original["id"]))
    response = ledger.put(original["id"], ledger.payload(amount="15.00"))
    assert response.status_code == 200
    assert response.json()["updated_at"] >= future.isoformat(timespec="microseconds") + "Z"
    assert response.json()["created_at"] == original["created_at"]
    stored = sql_record(ledger, original["id"])
    assert stored["updated_at"] >= future
    assert stored["amount"] == Decimal("15.00")


@pytest.mark.parametrize("changes,missing,field", [
    ({"amount": "0.00"}, None, "body.amount"),
    ({"amount": "-1.00"}, None, "body.amount"),
    ({"amount": 12.5}, None, "body.amount"),
    ({"type": "other"}, None, "body.type"),
    ({"category": " "}, None, "body.category"),
    ({"transaction_date": "2026-02-30"}, None, "body.transaction_date"),
    ({"note": None}, None, "body.note"),
    ({}, "amount", "body.amount"),
    ({"id": 999999999}, None, "body.id"),
    ({"created_at": "2026-11-15T00:00:00.000000Z"}, None, "body.created_at"),
])
def test_invalid_put_preserves_original(live_ledger, changes, missing, field):
    ledger = live_ledger
    original = create_owned(ledger)
    stored_before = sql_record(ledger, original["id"])
    data = ledger.payload(**changes)
    if missing:
        del data[missing]
    assert_error(ledger.put(original["id"], data), 422, "VALIDATION_ERROR", field)
    assert sql_record(ledger, original["id"]) == stored_before


def test_delete_empty_response_repeat_404_and_summary(live_ledger):
    ledger = live_ledger
    record = create_owned(ledger)
    response = ledger.client.delete(f"transactions/{record['id']}")
    assert response.status_code == 204
    assert response.content == b""
    assert sql_record(ledger, record["id"]) is None
    assert_error(ledger.client.delete(f"transactions/{record['id']}"), 404, "NOT_FOUND")
    assert ledger.client.get("transactions", params={"category": ledger.category}).json() == {"items": [], "total": 0}
    summary = ledger.client.get("summary", params={"category": ledger.category}).json()
    assert summary["total_income"] == summary["total_expense"] == summary["balance"] == "0.00"
    assert summary["expense_by_category"] == []


@pytest.mark.parametrize("record_id", ["0", "-1", "4294967296", "abc", "1.0", "1e3", "+1", "١"])
def test_invalid_ids_put_and_delete(live_ledger, record_id):
    assert_error(live_ledger.client.put(f"transactions/{record_id}", json=live_ledger.payload()), 422,
                 "VALIDATION_ERROR", "path.id")
    assert_error(live_ledger.client.delete(f"transactions/{record_id}"), 422, "VALIDATION_ERROR", "path.id")


def test_valid_but_missing_id_is_404(live_ledger):
    candidate = 4294967295
    if sql_record(live_ledger, candidate) is not None:
        pytest.skip("预定不存在ID已被真实数据占用，不触碰该记录")
    assert_error(live_ledger.client.put(f"transactions/{candidate}", json=live_ledger.payload()), 404, "NOT_FOUND")
    assert_error(live_ledger.client.delete(f"transactions/{candidate}"), 404, "NOT_FOUND")


def test_category_case_accents_and_sql_text_are_exact(live_ledger):
    ledger = live_ledger
    categories = [ledger.tag + "-A", ledger.tag + "-a", ledger.tag + "-é", ledger.tag + "-e", ledger.tag + "' OR 1=1 --"]
    for index, category in enumerate(categories):
        record = create_owned(ledger, category=category, amount=f"{index + 1}.00")
        listed = ledger.client.get("transactions", params={"category": category}).json()
        assert listed["total"] == 1
        assert listed["items"][0]["id"] == record["id"]
    for index, category in enumerate(categories):
        listed = ledger.client.get("transactions", params={"category": category}).json()
        summary = ledger.client.get("summary", params={"category": category}).json()
        assert listed["total"] == summary["transaction_count"] == 1
        assert summary["total_expense"] == f"{index + 1}.00"
        assert summary["expense_by_category"] == [{"category": category, "amount": f"{index + 1}.00"}]


def test_combined_date_type_filters_and_classification_totals(live_ledger):
    ledger = live_ledger
    for amount, kind, day in [("12.30", "expense", "2026-11-15"), ("4.50", "expense", "2026-11-16"),
                              ("100.00", "income", "2026-11-16"), ("99.00", "expense", "2026-11-17")]:
        create_owned(ledger, amount=amount, type=kind, transaction_date=day)
    params = {"category": ledger.category, "start_date": "2026-11-15", "end_date": "2026-11-16"}
    listed = ledger.client.get("transactions", params=params).json()
    summary = ledger.client.get("summary", params=params).json()
    assert listed["total"] == summary["transaction_count"] == 3
    assert [row["transaction_date"] for row in listed["items"]] == ["2026-11-16", "2026-11-16", "2026-11-15"]
    assert summary["total_income"] == "100.00"
    assert summary["total_expense"] == "16.80"
    assert summary["balance"] == "83.20"
    assert summary["expense_by_category"] == [{"category": ledger.category, "amount": "16.80"}]
    params["type"] = "expense"
    listed = ledger.client.get("transactions", params=params).json()
    summary = ledger.client.get("summary", params=params).json()
    assert listed["total"] == summary["transaction_count"] == 2
    assert summary["total_income"] == "0.00"
    assert summary["balance"] == "-16.80"
