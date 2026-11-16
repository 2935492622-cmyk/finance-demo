"""HTTP contracts: strict request text, Decimal internals, fixed output text."""

from datetime import UTC, date, datetime
from decimal import Decimal
import re
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StrictStr, WithJsonSchema, field_serializer, field_validator


AMOUNT_PATTERN = r"^(0|[1-9][0-9]{0,7})\.[0-9]{2}$"
DATE_PATTERN = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
TransactionType = Literal["income", "expense"]


def parse_money(value) -> Decimal:
    if type(value) is not str or not re.fullmatch(AMOUNT_PATTERN, value):
        raise ValueError("金额必须是固定两位小数的十进制字符串")
    amount = Decimal(value)
    if amount <= 0:
        raise ValueError("金额必须大于 0")
    return amount


def parse_date(value) -> date:
    if type(value) is not str or not re.fullmatch(DATE_PATTERN, value):
        raise ValueError("日期必须是 YYYY-MM-DD 文本")
    parsed = date.fromisoformat(value)
    if parsed.year < 1000:
        raise ValueError("日期年份必须至少为 1000")
    return parsed


def parse_record_id(value) -> int:
    # Pydantic's default int coercion accepts "1.0"; URL IDs must instead be
    # actual ASCII decimal integers before checking the MySQL unsigned range.
    if type(value) is not str or not re.fullmatch(r"[0-9]+", value):
        raise ValueError("ID 必须是十进制正整数")
    return int(value)


def money_text(value: Decimal) -> str:
    return format(value.copy_abs() if value == 0 else value, ".2f")


MoneyInput = Annotated[
    Decimal,
    BeforeValidator(parse_money),
    WithJsonSchema({"type": "string", "pattern": AMOUNT_PATTERN, "examples": ["125.50"]}),
]
DateInput = Annotated[date, BeforeValidator(parse_date), WithJsonSchema({"type": "string", "format": "date"})]
RecordID = Annotated[int, Field(ge=1, le=4294967295), BeforeValidator(parse_record_id)]


class TransactionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: MoneyInput
    type: TransactionType
    category: StrictStr = Field(min_length=1, max_length=50)
    note: StrictStr = Field(default="", max_length=500)
    transaction_date: DateInput

    @field_validator("category", "note", mode="before")
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: Decimal
    type: TransactionType
    category: str
    note: str
    transaction_date: date
    created_at: datetime
    updated_at: datetime

    @field_serializer("amount", return_type=str)
    def serialize_amount(self, value: Decimal) -> str:
        return money_text(value)

    @field_serializer("created_at", "updated_at", return_type=str)
    def serialize_timestamp(self, value: datetime) -> str:
        aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        return aware.isoformat(timespec="microseconds").replace("+00:00", "Z")


class TransactionList(BaseModel):
    items: list[TransactionRead]
    total: int


class TransactionFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: TransactionType | None = None
    category: Annotated[StrictStr, Field(min_length=1, max_length=50)] | None = None
    start_date: DateInput | None = None
    end_date: DateInput | None = None

    @field_validator("category", mode="before")
    @classmethod
    def trim_category(cls, value):
        return value.strip() if isinstance(value, str) else value


class CategoryExpense(BaseModel):
    category: str
    amount: Decimal

    @field_serializer("amount", return_type=str)
    def serialize_amount(self, value: Decimal) -> str:
        return money_text(value)


class Summary(BaseModel):
    total_income: Decimal
    total_expense: Decimal
    balance: Decimal
    transaction_count: int
    expense_by_category: list[CategoryExpense]

    @field_serializer("total_income", "total_expense", "balance", return_type=str)
    def serialize_amount(self, value: Decimal) -> str:
        return money_text(value)


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    database: Literal["connected"] = "connected"
