"""ORM metadata mirrors database/schema.sql; it never creates tables."""

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Index, Numeric, text
from sqlalchemy.dialects.mysql import DATETIME, INTEGER, VARCHAR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="chk_transactions_amount"),
        CheckConstraint(
            "(type = 'income' AND CHAR_LENGTH(type) = 6) OR (type = 'expense' AND CHAR_LENGTH(type) = 7)",
            name="chk_transactions_type",
        ),
        CheckConstraint(
            "CHAR_LENGTH(TRIM(category)) BETWEEN 1 AND 50 AND CHAR_LENGTH(category) = CHAR_LENGTH(TRIM(category))",
            name="chk_transactions_category",
        ),
        Index("idx_transactions_date_id", "transaction_date", "id"),
        Index("idx_transactions_type_date", "type", "transaction_date"),
        Index("idx_transactions_category_date", "category", "transaction_date"),
        {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_0900_ai_ci"},
    )

    id: Mapped[int] = mapped_column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2, asdecimal=True), nullable=False)
    type: Mapped[str] = mapped_column(VARCHAR(7, charset="ascii", collation="ascii_bin"), nullable=False)
    category: Mapped[str] = mapped_column(VARCHAR(50, charset="utf8mb4", collation="utf8mb4_0900_as_cs"), nullable=False)
    note: Mapped[str] = mapped_column(VARCHAR(500), nullable=False, default="", server_default=text("''"))
    transaction_date: Mapped[date] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6), nullable=False, default=utc_now, server_default=text("CURRENT_TIMESTAMP(6)")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6), nullable=False, default=utc_now, onupdate=utc_now,
        server_default=text("CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)"),
    )
