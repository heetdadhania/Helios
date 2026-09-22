from fastapi import APIRouter
from app.api.v1.endpoints import auth, datasets, health, tenants

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["Tenants"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["Datasets"])
