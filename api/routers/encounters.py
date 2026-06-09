from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from api.db import get_db
from api import schemas

router = APIRouter(prefix="/encounters", tags=["encounters"])


@router.get("/", response_model=list[schemas.Encounter])
async def list_encounters(
    encounter_class: str | None = Query(default=None),
    start_after: str | None = Query(default=None, description="ISO date, e.g. 2022-01-01"),
    start_before: str | None = Query(default=None, description="ISO date, e.g. 2022-12-31"),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    filters = []
    params: dict = {"limit": limit, "offset": offset}

    if encounter_class:
        filters.append("encounter_class = :encounter_class")
        params["encounter_class"] = encounter_class
    if start_after:
        filters.append("period_start >= :start_after")
        params["start_after"] = start_after
    if start_before:
        filters.append("period_start <= :start_before")
        params["start_before"] = start_before

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    result = await db.execute(
        text(f"SELECT * FROM mart.fct_encounters {where} ORDER BY period_start DESC LIMIT :limit OFFSET :offset"),
        params,
    )
    return [schemas.Encounter(**row) for row in result.mappings().all()]
