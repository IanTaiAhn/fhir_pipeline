from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from api.db import get_db
from api import schemas

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/", response_model=list[schemas.Patient])
async def list_patients(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("SELECT * FROM mart.dim_patients ORDER BY patient_id LIMIT :limit OFFSET :offset"),
        {"limit": limit, "offset": offset},
    )
    rows = result.mappings().all()
    return [schemas.Patient(**row) for row in rows]


@router.get("/{patient_id}", response_model=schemas.Patient)
async def get_patient(patient_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT * FROM mart.dim_patients WHERE patient_id = :pid"),
        {"pid": patient_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Patient not found")
    return schemas.Patient(**row)


@router.get("/{patient_id}/conditions", response_model=list[schemas.Condition])
async def get_patient_conditions(patient_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT * FROM mart.dim_conditions WHERE patient_id = :pid ORDER BY onset_datetime DESC"),
        {"pid": patient_id},
    )
    return [schemas.Condition(**row) for row in result.mappings().all()]


@router.get("/{patient_id}/encounters", response_model=list[schemas.Encounter])
async def get_patient_encounters(patient_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT * FROM mart.fct_encounters WHERE patient_id = :pid ORDER BY period_start DESC"),
        {"pid": patient_id},
    )
    return [schemas.Encounter(**row) for row in result.mappings().all()]


@router.get("/{patient_id}/observations", response_model=list[schemas.Observation])
async def get_patient_observations(patient_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT * FROM mart.fct_observations WHERE patient_id = :pid ORDER BY effective_datetime DESC"),
        {"pid": patient_id},
    )
    return [schemas.Observation(**row) for row in result.mappings().all()]
