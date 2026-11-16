from datetime import date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas import Summary, TransactionRead, TransactionWrite, money_text


def valid_payload(**overrides):
    return {"amount": "125.50", "type": "expense", "category": "餐饮",
            "note": "午餐", "transaction_date": "2026-11-16", **overrides}


@pytest.mark.parametrize("value", ["0.01", "99999999.99", "0.10", "1000.00"])
def test_valid_money_stays_decimal(value):
    payload = TransactionWrite.model_validate(valid_payload(amount=value))
    assert type(payload.amount) is Decimal
    assert payload.amount == Decimal(value)


@pytest.mark.parametrize("value", ["0.00", "-1.00", "100000000.00", "1.001", "1", "1.2", "01.00",
                                  "1e2", "NaN", "Infinity", " 1.00", "1.00\n", 1.23, 1, True, None])
def test_invalid_money_rejected(value):
    with pytest.raises(ValidationError):
        TransactionWrite.model_validate(valid_payload(amount=value))


@pytest.mark.parametrize("value", ["Income", "income ", "EXPENSE", "transfer", "", None, 1])
def test_invalid_type(value):
    with pytest.raises(ValidationError):
        TransactionWrite.model_validate(valid_payload(type=value))


def test_unicode_trim_and_length_limits():
    payload = TransactionWrite.model_validate(valid_payload(category="\u3000" + "账" * 50 + "\t", note="  " + "🙂" * 500 + "\n"))
    assert payload.category == "账" * 50
    assert payload.note == "🙂" * 500
    for overrides in [{"category": " \u3000\t"}, {"category": "账" * 51}, {"note": "🙂" * 501},
                      {"category": None}, {"note": None}, {"category": 123}, {"note": False}]:
        with pytest.raises(ValidationError):
            TransactionWrite.model_validate(valid_payload(**overrides))


@pytest.mark.parametrize("value", ["2026-02-30", "0999-12-31", "2026-2-01", "2026-11-16T00:00:00",
                                  "", 1794787200, None])
def test_invalid_date(value):
    with pytest.raises(ValidationError):
        TransactionWrite.model_validate(valid_payload(transaction_date=value))


@pytest.mark.parametrize("value", ["1000-01-01", "9999-12-31", "2024-02-29"])
def test_valid_date_boundary(value):
    assert TransactionWrite.model_validate(valid_payload(transaction_date=value)).transaction_date == date.fromisoformat(value)


def test_required_fields_and_extra_readonly_fields():
    payload = valid_payload()
    del payload["note"]
    assert TransactionWrite.model_validate(payload).note == ""
    for field in ["amount", "type", "category", "transaction_date"]:
        incomplete = valid_payload()
        del incomplete[field]
        with pytest.raises(ValidationError):
            TransactionWrite.model_validate(incomplete)
    for field in ["id", "created_at", "unknown"]:
        with pytest.raises(ValidationError):
            TransactionWrite.model_validate(valid_payload(**{field: "unexpected"}))


def test_response_has_exact_money_and_utc_timestamp():
    record = TransactionRead(
        id=1, amount=Decimal("0.10"), type="income", category="工资", note="",
        transaction_date=date(2026, 11, 16), created_at=datetime(2026, 11, 16, 1, 2, 3, 42),
        updated_at=datetime(2026, 11, 16, 1, 2, 3, 42),
    ).model_dump(mode="json")
    assert record["amount"] == "0.10"
    assert record["created_at"] == "2026-11-16T01:02:03.000042Z"
    assert record["transaction_date"] == "2026-11-16"


def test_summary_keeps_large_totals_negative_balance_and_zero():
    summary = Summary(total_income=Decimal("199999999.98"), total_expense=Decimal("200000000.00"),
                      balance=Decimal("-0.02"), transaction_count=3, expense_by_category=[])
    assert summary.model_dump(mode="json")["total_income"] == "199999999.98"
    assert summary.model_dump(mode="json")["balance"] == "-0.02"
    assert money_text(Decimal("-0.00")) == "0.00"
