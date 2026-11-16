from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_session
from ..schemas import Health


router = APIRouter(prefix="/api", tags=["健康检查"])


@router.get("/health", response_model=Health)
def health(session: Annotated[Session, Depends(get_session)]):
    session.execute(text("SELECT 1")).scalar_one()
    return Health()
