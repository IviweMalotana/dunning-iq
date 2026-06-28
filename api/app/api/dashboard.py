"""Recovery dashboard endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.api import DashboardSummary, ReasonStat, TimePoint
from app.services import stats

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db)) -> DashboardSummary:
    return stats.dashboard_summary(db)


@router.get("/timeseries", response_model=list[TimePoint])
def timeseries(weeks: int = 12, db: Session = Depends(get_db)) -> list[TimePoint]:
    return stats.dashboard_timeseries(db, weeks=weeks)


@router.get("/by-reason", response_model=list[ReasonStat])
def by_reason(db: Session = Depends(get_db)) -> list[ReasonStat]:
    return stats.dashboard_by_reason(db)
