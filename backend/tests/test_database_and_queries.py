from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import OperationalError
from sqlalchemy.schema import CreateTable

from app import crud, database
from app.config import Settings
from app.exceptions import DatabaseUnavailable
from app.models import Transaction
from app.schemas import TransactionFilters, TransactionWrite
from test_validation import valid_payload


def test_model_types_constraints_and_indexes_match_schema():
    table = Transaction.__table__
    assert table.c.id.type.unsigned is True
    assert (table.c.amount.type.precision, table.c.amount.type.scale, table.c.amount.type.asdecimal) == (10, 2, True)
    assert table.c.category.type.collation == "utf8mb4_0900_as_cs"
    assert table.c.type.type.collation == "ascii_bin"
    assert {index.name for index in table.indexes} == {
        "idx_transactions_date_id", "idx_transactions_type_date", "idx_transactions_category_date"
    }
    assert {constraint.name for constraint in table.constraints if constraint.name} == {
        "chk_transactions_amount", "chk_transactions_type", "chk_transactions_category"
    }
    ddl = str(CreateTable(table).compile(dialect=mysql.dialect()))
    assert "ON UPDATE CURRENT_TIMESTAMP(6)" in ddl
    assert "ENGINE=InnoDB" in ddl


def test_session_sets_utc_and_rejects_non_strict_mode():
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = ("NO_ENGINE_SUBSTITUTION",)
    with pytest.raises(DatabaseUnavailable):
        database.configure_mysql_connection(connection, None)
    assert cursor.execute.call_args_list[0].args == ("SET SESSION time_zone = '+00:00'",)
    cursor.fetchone.return_value = ("STRICT_TRANS_TABLES,NO_ZERO_DATE",)
    database.configure_mysql_connection(connection, None)


def test_database_error_rolls_back_and_closes(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(database, "get_engine", lambda: object())
    monkeypatch.setattr(database, "sessionmaker", lambda **_kwargs: lambda: session)
    dependency = database.get_session()
    assert next(dependency) is session
    with pytest.raises(DatabaseUnavailable):
        dependency.throw(OperationalError("private SQL", {}, Exception("private secret")))
    session.rollback.assert_called_once()
    session.close.assert_called_once()


def test_other_exception_also_rolls_back(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(database, "get_engine", lambda: object())
    monkeypatch.setattr(database, "sessionmaker", lambda **_kwargs: lambda: session)
    dependency = database.get_session()
    next(dependency)
    with pytest.raises(RuntimeError):
        dependency.throw(RuntimeError("controlled unit fault"))
    session.rollback.assert_called_once()
    session.close.assert_called_once()


def test_broken_connection_cleanup_does_not_mask_database_error(monkeypatch):
    session = MagicMock()
    fault = OperationalError("private SQL", {}, Exception("private secret"))
    session.rollback.side_effect = fault
    session.close.side_effect = fault
    monkeypatch.setattr(database, "get_engine", lambda: object())
    monkeypatch.setattr(database, "sessionmaker", lambda **_kwargs: lambda: session)
    dependency = database.get_session()
    next(dependency)
    with pytest.raises(DatabaseUnavailable):
        dependency.throw(fault)
    session.rollback.assert_called_once()
    session.close.assert_called_once()


def test_invalid_database_settings_are_unavailable_not_raw_validation_error(monkeypatch):
    def invalid_settings():
        return Settings(_env_file=None, db_name="wrong_database")
    database.get_engine.cache_clear()
    monkeypatch.setattr(database, "get_settings", invalid_settings)
    with pytest.raises(DatabaseUnavailable):
        database.get_engine()
    database.get_engine.cache_clear()


def test_create_uses_one_timestamp_and_commits_before_return():
    session = MagicMock()
    payload = TransactionWrite.model_validate(valid_payload())
    record = crud.create_transaction(session, payload)
    assert record.amount == Decimal("125.50")
    assert record.created_at == record.updated_at
    assert record.created_at.tzinfo is None
    session.add.assert_called_once_with(record)
    session.commit.assert_called_once()


def test_create_does_not_report_success_after_commit_failure():
    session = MagicMock()
    session.commit.side_effect = OperationalError("unit fault", {}, Exception("unavailable"))
    with pytest.raises(OperationalError):
        crud.create_transaction(session, TransactionWrite.model_validate(valid_payload()))


def test_summary_uses_shared_parameterized_filters_and_decimal():
    session = MagicMock()
    totals = SimpleNamespace(income=Decimal("0.10") + Decimal("0.20"), expense=Decimal("1.00"), count=3)
    session.execute.return_value.one.return_value = totals
    session.execute.return_value.all.return_value = [SimpleNamespace(category="餐饮", amount=Decimal("1.00"))]
    filters = TransactionFilters.model_validate({"category": "餐饮", "start_date": "2026-11-01", "end_date": "2026-11-30"})
    result = crud.get_summary(session, filters).model_dump(mode="json")
    assert result["total_income"] == "0.30"
    assert result["balance"] == "-0.70"
    assert result["expense_by_category"] == [{"category": "餐饮", "amount": "1.00"}]
    for call in session.execute.call_args_list:
        compiled = call.args[0].compile(dialect=mysql.dialect())
        assert "餐饮" not in str(compiled)
        assert "餐饮" in compiled.params.values()
        assert "transaction_date >=" in str(compiled)
        assert "transaction_date <=" in str(compiled)


def test_empty_summary_is_zero():
    session = MagicMock()
    session.execute.return_value.one.return_value = SimpleNamespace(income=None, expense=None, count=0)
    session.execute.return_value.all.return_value = []
    assert crud.get_summary(session, TransactionFilters()).model_dump(mode="json") == {
        "total_income": "0.00", "total_expense": "0.00", "balance": "0.00",
        "transaction_count": 0, "expense_by_category": [],
    }


def test_list_has_no_limit_and_deterministic_sort():
    session = MagicMock()
    session.scalars.return_value.all.return_value = []
    assert crud.list_transactions(session, TransactionFilters()) == []
    statement = str(session.scalars.call_args.args[0].compile(dialect=mysql.dialect()))
    assert "ORDER BY transactions.transaction_date DESC, transactions.id DESC" in statement
    assert "LIMIT" not in statement


def test_settings_enforce_project_db_and_hide_password():
    settings = Settings(_env_file=None, db_password="unit-only-placeholder")
    assert "unit-only-placeholder" not in repr(settings)
    with pytest.raises(ValueError):
        Settings(_env_file=None, db_name="some_other_project")
