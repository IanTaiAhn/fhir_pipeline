from fastapi import FastAPI
from api.routers import patients, conditions, encounters

app = FastAPI(
    title="FHIR Pipeline API",
    description="Query layer over the FHIR R4 mart schema.",
    version="1.0.0",
)

app.include_router(patients.router)
app.include_router(conditions.router)
app.include_router(encounters.router)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
