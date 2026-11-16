"""SQL-only operations and one shared filter builder; no alternate storage."""

from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from .exceptions import APIError
from .models import Transaction, utc_now
from .schemas import CategoryExpense, Summary, TransactionFilters, TransactionWrite


def filter_conditions(filters: TransactionFilters):
    conditions = []
    if filters.type is not None:
        conditions.append(Transaction.type == filters.type)
    if filters.category is not None:
        conditions.append(Transaction.category == filters.category)
    if filters.start_date is not None:
        conditions.append(Transaction.transaction_date >= filters.start_date)
    if filters.end_date is not None:
        conditions.append(Transaction.transaction_date <= filters.end_date)
    return conditions


def create_transaction(session: Session, payload: TransactionWrite) -> Transaction:
    now = utc_now()
    record = Transaction(**payload.model_dump(), created_at=now, updated_at=now)
    session.add(record)
    session.commit()
    # expire_on_commit=False preserves committed values without a second read.
    return record


def get_transaction_for_write(session: Session, record_id: int) -> Transaction:
    # A row lock keeps a concurrent edit/delete from making the checked record
    # disappear before this request commits. It does not add version conflicts.
    record = session.get(Transaction, record_id, with_for_update=True)
    if record is None:
        raise APIError(404, "NOT_FOUND", "收支记录不存在")
    return record


def update_transaction(session: Session, record_id: int, payload: TransactionWrite) -> Transaction:
    record = get_transaction_for_write(session, record_id)
    for field, value in payload.model_dump().items():
        setattr(record, field, value)
    # Preserve monotonicity even if the host clock moved backwards. The DB
    # stores UTC-naive DATETIME, so both compared values use the same basis.
    record.updated_at = max(utc_now(), record.updated_at)
    # If max kept the old value, SQLAlchemy would normally omit an unchanged
    # attribute and run its onupdate default instead. Force this chosen value
    # into UPDATE so a backwards clock cannot override the monotonic result.
    flag_modified(record, "updated_at")
    session.commit()
    return record


def delete_transaction(session: Session, record_id: int) -> None:
    record = get_transaction_for_write(session, record_id)
    session.delete(record)
    session.commit()


def list_transactions(session: Session, filters: TransactionFilters) -> list[Transaction]:
    statement = select(Transaction).where(*filter_conditions(filters)).order_by(
        Transaction.transaction_date.desc(), Transaction.id.desc()
    )
    return list(session.scalars(statement).all())


def get_summary(session: Session, filters: TransactionFilters) -> Summary:
    conditions = filter_conditions(filters)
    zero = Decimal("0.00")
    totals = session.execute(
        select(
            func.sum(case((Transaction.type == "income", Transaction.amount), else_=zero)).label("income"),
            func.sum(case((Transaction.type == "expense", Transaction.amount), else_=zero)).label("expense"),
            func.count(Transaction.id).label("count"),
        ).where(*conditions)
    ).one()
    income = totals.income if totals.income is not None else zero
    expense = totals.expense if totals.expense is not None else zero
    grouped_amount = func.sum(Transaction.amount).label("amount")
    groups = session.execute(
        select(Transaction.category, grouped_amount)
        .where(*conditions, Transaction.type == "expense")
        .group_by(Transaction.category)
        .order_by(grouped_amount.desc(), Transaction.category.asc())
    ).all()
    return Summary(
        total_income=income,
        total_expense=expense,
        balance=income - expense,
        transaction_count=totals.count,
        expense_by_category=[CategoryExpense(category=row.category, amount=row.amount) for row in groups],
    )
