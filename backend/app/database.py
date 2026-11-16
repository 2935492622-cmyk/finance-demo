"""Synchronous MySQL engine and one Session per request."""

from collections.abc import Generator
from functools import lru_cache

from pydantic import ValidationError
from sqlalchemy import URL, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings
from .exceptions import DatabaseUnavailable


def configure_mysql_connection(dbapi_connection, _connection_record) -> None:
    """Only session settings change; never alter shared server globals."""
    with dbapi_connection.cursor() as cursor:
        cursor.execute("SET SESSION time_zone = '+00:00'")
        cursor.execute("SELECT @@SESSION.sql_mode")
        modes = set((cursor.fetchone()[0] or "").upper().split(","))
        if not modes.intersection({"STRICT_TRANS_TABLES", "STRICT_ALL_TABLES"}):
            raise DatabaseUnavailable()


@lru_cache
def get_engine() -> Engine:
    try:
        settings = get_settings()
    except ValidationError:
        # Invalid local DB settings are an unavailable dependency, not a raw
        # Pydantic error (which can include configuration values).
        raise DatabaseUnavailable() from None
    url = URL.create(
        "mysql+pymysql",
        username=settings.db_user,
        password=settings.db_password.get_secret_value(),
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        query={"charset": "utf8mb4"},
    )
    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=1800,
        hide_parameters=True,
        connect_args={"connect_timeout": 3, "read_timeout": 5, "write_timeout": 5},
    )
    event.listen(engine, "connect", configure_mysql_connection)
    return engine


def get_session() -> Generator[Session, None, None]:
    session = sessionmaker(bind=get_engine(), expire_on_commit=False)()
    try:
        yield session
    except SQLAlchemyError:
        rollback_safely(session)
        raise DatabaseUnavailable() from None
    except Exception:
        rollback_safely(session)
        raise
    finally:
        try:
            session.close()
        except SQLAlchemyError:
            # A disconnected connection may fail again during cleanup; do not
            # replace the original controlled response with a cleanup error.
            pass


def rollback_safely(session: Session) -> None:
    try:
        session.rollback()
    except SQLAlchemyError:
        # A lost connection cannot perform a second rollback. Closing the
        # Session below releases it without exposing its driver exception.
        pass
