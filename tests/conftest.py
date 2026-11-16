"""Opt-in, real HTTP/MySQL QA fixtures. No database is created or reset."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import httpx
import pymysql
import pytest
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


class LiveLedger:
    """Own only returned IDs whose expected test category and note still match."""

    def __init__(self, client, connection):
        self.client = client
        self.connection = connection
        self.tag = f"qa-{uuid4().hex[:20]}"
        self.category = self.tag
        self.created = {}

    def payload(self, **changes):
        data = {
            "amount": "12.30",
            "type": "expense",
            "category": self.category,
            "note": self.tag,
            "transaction_date": "2026-11-15",
        }
        data.update(changes)
        return data

    def post(self, data):
        response = self.client.post("transactions", json=data)
        # Register even a wrongly accepted invalid request, so a failed test can clean up.
        if response.status_code == 201:
            body = response.json()
            record_id = body.get("id")
            category = data.get("category")
            note = data.get("note", "")
            if isinstance(record_id, int) and isinstance(category, str) and isinstance(note, str):
                self.created[record_id] = (category.strip(), note.strip())
        return response

    def put(self, record_id, data):
        if record_id not in self.created:
            raise ValueError("QA updates only its own created IDs")
        response = self.client.put(f"transactions/{record_id}", json=data)
        if response.status_code == 200:
            category = data.get("category")
            note = data.get("note", "")
            if isinstance(category, str) and isinstance(note, str):
                # Full PUT may change category or omit/clear note. Follow the
                # new expected values rather than leaving test rows behind.
                self.created[record_id] = (category.strip(), note.strip())
        return response

    def rows(self, category=None):
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, amount, type, category, note, transaction_date, "
                "created_at, updated_at FROM transactions WHERE category=%s "
                "ORDER BY transaction_date DESC, id DESC",
                (self.category if category is None else category,),
            )
            return list(cursor.fetchall())

    def cleanup(self):
        with self.connection.cursor() as cursor:
            for record_id, (category, note) in self.created.items():
                cursor.execute(
                    "DELETE FROM transactions WHERE id=%s AND category=%s AND note=%s",
                    (record_id, category, note),
                )


@pytest.fixture
def live_ledger():
    if os.environ.get("FINANCE_QA_INTEGRATION") != "1":
        pytest.skip("真实 MySQL 验收尚未启用；就绪后设置 FINANCE_QA_INTEGRATION=1")
    env_path = ROOT / "backend/.env"
    if not env_path.is_file():
        pytest.skip("backend/.env 不存在，真实数据库验收受阻")
    config = dotenv_values(env_path)
    if config.get("DB_NAME") != "finance_demo":
        pytest.fail("QA 只允许连接 finance_demo", pytrace=False)
    if not config.get("DB_USER") or not config.get("DB_PASSWORD"):
        pytest.fail("backend/.env 缺少专用数据库账号或密码", pytrace=False)

    api_url = os.environ.get("FINANCE_QA_API_URL", "http://127.0.0.1:8000/api/")
    parsed = httpx.URL(api_url)
    if parsed.host not in {"127.0.0.1", "localhost", "::1"} or parsed.username or parsed.password:
        pytest.fail("QA API 地址必须是无嵌入凭据的本地地址", pytrace=False)

    connection = None
    failure = None
    try:
        connection = pymysql.connect(
            host=config.get("DB_HOST", "127.0.0.1"),
            port=int(config.get("DB_PORT", "3306")),
            user=config["DB_USER"],
            password=config["DB_PASSWORD"],
            database="finance_demo",
            charset="utf8mb4",
            autocommit=True,
            connect_timeout=3,
            read_timeout=5,
            write_timeout=5,
            cursorclass=pymysql.cursors.DictCursor,
        )
    except (pymysql.MySQLError, ValueError) as exc:
        failure = f"真实数据库连接失败（{type(exc).__name__}），请本地检查配置；凭据未输出"
    if failure:
        pytest.fail(failure, pytrace=False)

    with httpx.Client(base_url=api_url.rstrip("/") + "/", timeout=10) as client:
        ledger = LiveLedger(client, connection)
        try:
            try:
                health = client.get("health")
            except httpx.HTTPError:
                pytest.fail("本地后端不可连接，真实接口验收受阻", pytrace=False)
            if health.status_code != 200:
                pytest.fail(f"真实后端 health 非健康（HTTP {health.status_code}）", pytrace=False)
            assert health.json() == {"status": "ok", "database": "connected"}
            with connection.cursor() as cursor:
                cursor.execute("SELECT DATABASE() AS db, VERSION() AS version, @@sql_mode AS sql_mode")
                info = cursor.fetchone()
            assert info["db"] == "finance_demo"
            assert str(info["version"]).startswith("8.")
            assert {"STRICT_TRANS_TABLES", "STRICT_ALL_TABLES"}.intersection(info["sql_mode"].split(","))
            yield ledger
        finally:
            try:
                ledger.cleanup()
            finally:
                connection.close()
