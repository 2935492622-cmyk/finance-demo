from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from .. import crud
from ..database import get_session
from ..exceptions import APIError
from ..schemas import RecordID, Summary, TransactionFilters, TransactionList, TransactionRead, TransactionWrite


router = APIRouter(prefix="/api", tags=["记账"])


def get_filters(filters: Annotated[TransactionFilters, Query()]) -> TransactionFilters:
    if filters.start_date and filters.end_date and filters.start_date > filters.end_date:
        raise APIError(422, "VALIDATION_ERROR", "请求参数不合法", [
            {"field": "query.start_date", "message": "起始日期不能晚于结束日期"}
        ])
    return filters


SessionDependency = Annotated[Session, Depends(get_session)]
FiltersDependency = Annotated[TransactionFilters, Depends(get_filters)]


@router.post("/transactions", response_model=TransactionRead, status_code=201)
def create_transaction(payload: TransactionWrite, session: SessionDependency):
    return crud.create_transaction(session, payload)


@router.put("/transactions/{id}", response_model=TransactionRead)
def update_transaction(id: RecordID, payload: TransactionWrite, session: SessionDependency):
    return crud.update_transaction(session, id, payload)


@router.delete("/transactions/{id}", status_code=204, response_class=Response)
def delete_transaction(id: RecordID, session: SessionDependency) -> Response:
    crud.delete_transaction(session, id)
    return Response(status_code=204)


@router.get("/transactions", response_model=TransactionList)
def list_transactions(filters: FiltersDependency, session: SessionDependency):
    items = crud.list_transactions(session, filters)
    return TransactionList(items=items, total=len(items))


@router.get("/summary", response_model=Summary)
def summary(filters: FiltersDependency, session: SessionDependency):
    return crud.get_summary(session, filters)
