from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.auth import router as auth_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.assistant import router as assistant_router
from app.api.v1.catalog import departments_router, users_router, wards_router, zones_router
from app.api.v1.complaints import router as complaints_router
from app.api.v1.operations import router as operations_router
from app.api.v1.worker import router as worker_router
from app.config import settings

app = FastAPI(title="NagarIQ API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(analytics_router)
app.include_router(assistant_router)
app.include_router(users_router)
app.include_router(wards_router)
app.include_router(zones_router)
app.include_router(departments_router)
app.include_router(complaints_router)
app.include_router(operations_router)
app.include_router(worker_router)

upload_root = Path(settings.upload_dir).resolve()
upload_root.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_root)), name="uploads")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
