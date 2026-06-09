from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from api.db import get_db
from api import schemas

router = APIRouter(prefix="/conditions", tags=["conditions"])


@router.get("/", response_model=list[schemas.Condition])
async def list_conditions(
    snomed_code: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    filters = []
    params: dict = {"limit": limit, "offset": offset}

    if snomed_code:
        filters.append("code_value = :snomed_code")
        params["snomed_code"] = snomed_code
    if status:
        filters.append("clinical_status = :status")
        params["status"] = status

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    result = await db.execute(
        text(f"SELECT * FROM mart.dim_conditions {where} ORDER BY onset_datetime DESC LIMIT :limit OFFSET :offset"),
        params,
    )
    return [schemas.Condition(**row) for row in result.mappings().all()]
