"""Read only the known page-created demo IDs using local .env credentials."""

from datetime import date, datetime
from decimal import Decimal
import json
from pathlib import Path
import sys

from dotenv import dotenv_values
import pymysql

ROOT = Path(__file__).resolve().parents[1]


def main():
    state_path = Path(sys.argv[1]).resolve()
    if state_path != ROOT / "tests/.p0-demo-state.json":
        raise ValueError("Unsupported QA state path")
    state = json.loads(state_path.read_text())
    expected = state["created_records"]
    if len(expected) != 2 or any(not row["note"].startswith(state["run_marker"]) for row in expected):
        raise ValueError("Expected exactly two identified page-created demo records")
    config = dotenv_values(ROOT / "backend/.env")
    if config.get("DB_NAME") != "finance_demo":
        raise ValueError("Only finance_demo is allowed")
    connection = pymysql.connect(
        host=config.get("DB_HOST", "127.0.0.1"), port=int(config.get("DB_PORT", "3306")),
        user=config["DB_USER"], password=config["DB_PASSWORD"], database="finance_demo",
        charset="utf8mb4", autocommit=True, connect_timeout=3, read_timeout=5,
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE() AS db, VERSION() AS version")
            info = cursor.fetchone()
            cursor.execute(
                "SELECT id, amount, type, category, note, transaction_date, created_at, updated_at "
                "FROM transactions WHERE id IN (%s,%s) ORDER BY id",
                tuple(row["id"] for row in expected),
            )
            rows = list(cursor.fetchall())
            # Global totals contain only aggregates, not any other user's notes.
            cursor.execute(
                "SELECT COUNT(*) AS transaction_count, "
                "COALESCE(SUM(CASE WHEN type='income' THEN amount ELSE 0 END),0) AS total_income, "
                "COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END),0) AS total_expense "
                "FROM transactions"
            )
            totals = cursor.fetchone()
        if len(rows) != 2:
            raise ValueError("The two page-created IDs are not both present in MySQL")
        by_id = {row["id"]: row for row in expected}
        for row in rows:
            before = by_id[row["id"]]
            if not isinstance(row["amount"], Decimal):
                raise ValueError("MySQL amount is not Decimal")
            if row["amount"] != Decimal(before["amount"]):
                raise ValueError("MySQL amount differs from the page POST response")
            for key in ["type", "category", "note"]:
                if row[key] != before[key]:
                    raise ValueError(f"MySQL {key} differs from the page POST response")
            if row["transaction_date"] != date.fromisoformat(before["transaction_date"]):
                raise ValueError("MySQL transaction_date differs from the page POST response")
            for key in ["created_at", "updated_at"]:
                if row[key].isoformat(timespec="microseconds") + "Z" != before[key]:
                    raise ValueError(f"MySQL {key} differs from the page POST response")
            row["amount_python_type"] = type(row["amount"]).__name__
        totals["balance"] = totals["total_income"] - totals["total_expense"]

        def serialize(value):
            if isinstance(value, Decimal):
                return format(value, ".2f")
            if isinstance(value, datetime):
                return value.isoformat(timespec="microseconds") + "Z"
            if isinstance(value, date):
                return value.isoformat()
            raise TypeError("Unsupported evidence value")

        print(json.dumps({
            "database": info["db"], "mysql_version": info["version"],
            "verified_demo_records": rows, "sql_totals": totals,
        }, ensure_ascii=False, default=serialize))
    finally:
        connection.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Do not print the underlying driver exception, configuration or password.
        print(f"SQL evidence verification failed ({type(exc).__name__}); credentials withheld", file=sys.stderr)
        sys.exit(1)
