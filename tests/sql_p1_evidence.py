"""P1 readback/cleanup limited to registered QA IDs; protected demo IDs stay intact."""

from datetime import date, datetime
from decimal import Decimal
import json
from pathlib import Path
import sys

from dotenv import dotenv_values
import pymysql

ROOT = Path(__file__).resolve().parents[1]


def normalize(value):
    if isinstance(value, Decimal):
        return format(value, ".2f")
    if isinstance(value, datetime):
        return value.isoformat(timespec="microseconds") + "Z"
    if isinstance(value, date):
        return value.isoformat()
    return value


def main():
    state = json.loads((ROOT / "tests/.p1-demo-state.json").read_text())
    own = state["created_records"]
    protected = state["protected_records"]
    protected_ids = {item["id"] for item in protected}
    if not state.get("baseline_captured") or any(item["id"] in protected_ids for item in own):
        raise ValueError("Invalid ownership or protected IDs")
    own_ids = [item["id"] for item in own]
    if len(own_ids) != len(set(own_ids)) or any(type(value) is not int or value <= 0 for value in own_ids):
        raise ValueError("Invalid registered QA IDs")
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
            def read(record_id):
                cursor.execute("SELECT * FROM transactions WHERE id=%s", (record_id,))
                row = cursor.fetchone()
                return None if row is None else {key: normalize(value) for key, value in row.items()}

            for expected in protected:
                if read(expected["id"]) != expected:
                    raise ValueError("Protected demo record changed")
            cleanup = "--cleanup" in sys.argv
            rows = []
            cleaned_ids = []
            for expected in own:
                actual = read(expected["id"])
                if cleanup:
                    if actual is None:
                        continue
                    cursor.execute("DELETE FROM transactions WHERE id=%s AND category=%s AND note=%s",
                                   (expected["id"], expected["category"], expected["note"]))
                    if cursor.rowcount != 1:
                        raise ValueError("QA cleanup ownership fields no longer match")
                    cleaned_ids.append(expected["id"])
                elif expected.get("deleted"):
                    if actual is not None:
                        raise ValueError("Deleted QA record still exists")
                    rows.append({"id": expected["id"], "deleted": True})
                else:
                    if actual != expected:
                        raise ValueError("QA SQL record differs from latest page response")
                    rows.append(actual)
            for expected in protected:
                if read(expected["id"]) != expected:
                    raise ValueError("Protected demo record changed during QA")
        print(json.dumps({"database": "finance_demo", "verified_records": rows,
                          "protected_ids_unchanged": sorted(protected_ids), "cleaned_ids": cleaned_ids}, ensure_ascii=False))
    finally:
        connection.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"P1 SQL verification failed ({type(exc).__name__}); credentials withheld", file=sys.stderr)
        sys.exit(1)
