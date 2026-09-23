from fastapi import APIRouter
from app.api.v1.endpoints import auth, datasets, health, tenants
from app.api.db_connections import router as db_connections_router
from app.api.api_ingest import router as api_ingest_router
from app.api.api_keys import router as api_keys_router

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["Datasets"])
api_router.include_router(db_connections_router, prefix="/db-connections", tags=["Database Connections"])
api_router.include_router(api_ingest_router, prefix="/ingest", tags=["API Ingestion"])
api_router.include_router(api_keys_router, prefix="/api-keys", tags=["API Keys"])
