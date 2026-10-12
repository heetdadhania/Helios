from fastapi import APIRouter
from app.api.v1.endpoints import auth, datasets, health, tenants
from app.api.db_connections import router as db_connections_router
from app.api.api_ingest import router as api_ingest_router
from app.api.api_keys import router as api_keys_router
from app.api.pipeline_health import router as pipeline_health_router
from app.api.export import router as export_router
from app.api.notifications import router as notifications_router
from app.api.history import router as history_router
from app.api.support import router as support_router
from app.api.oversight import router as oversight_router

from app.api.confirmations import router as confirmations_router
from app.api.uploads import router as uploads_router
from app.api.dashboard import router as dashboard_router
from app.api.data_quality import router as data_quality_router
from app.api.team import router as team_router

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])
api_router.include_router(team_router, prefix="/team-members", tags=["Team Members"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["Datasets"])
api_router.include_router(db_connections_router, prefix="/db-connections", tags=["Database Connections"])
api_router.include_router(api_ingest_router, prefix="/ingest", tags=["API Ingestion"])
api_router.include_router(api_keys_router, prefix="/api-keys", tags=["API Keys"])
api_router.include_router(pipeline_health_router, prefix="/pipeline", tags=["Pipeline Health"])
api_router.include_router(export_router, prefix="/export", tags=["Export"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(history_router, prefix="/history", tags=["History"])
api_router.include_router(support_router, prefix="/support", tags=["Support"])
api_router.include_router(oversight_router, prefix="/oversight", tags=["Admin Oversight"])
api_router.include_router(confirmations_router, prefix="/uploads", tags=["Confirmations"])
api_router.include_router(uploads_router, prefix="/uploads", tags=["Uploads"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(data_quality_router, prefix="/data-quality", tags=["Data Quality"])
