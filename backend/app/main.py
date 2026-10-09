import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from app.api.v1.api import api_router
from app.core.config import settings
from app.core.exceptions import HeliosException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("helios")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager handling startup and shutdown events."""
    logger.info("Initializing %s...", settings.PROJECT_NAME)
    logger.info("Environment: %s", settings.ENVIRONMENT)
    logger.info("Databricks Host: %s", settings.DATABRICKS_SERVER_HOSTNAME)
    logger.info("Databricks Catalog: %s", settings.DATABRICKS_CATALOG)
    yield
    logger.info("Shutting down %s...", settings.PROJECT_NAME)
    from app.db.base import close_connection_pool
    close_connection_pool()


def create_application() -> FastAPI:
    """Instantiate and configure the FastAPI application instance."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        description="Multi-tenant data platform backend integrating with Databricks Unity Catalog and Delta Lake.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
    )

    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include Direct Auth Router (/api/auth/login, /api/auth/me)
    from app.api.auth import router as auth_router
    app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])

    # Include Ingestion Uploads Confirmation Router (/api/uploads/pending, /api/uploads/{batch_id}/preview, /api/uploads/{batch_id}/confirm)
    from app.api.confirmations import router as confirmations_router
    app.include_router(confirmations_router, prefix="/api/uploads", tags=["Confirmations"])

    # Include Ingestion Uploads Router (/api/uploads)
    from app.api.uploads import router as uploads_router
    app.include_router(uploads_router, prefix="/api/uploads", tags=["Uploads"])

    # Include Database Connections Ingestion Router (/api/db-connections)
    from app.api.db_connections import router as db_connections_router
    app.include_router(db_connections_router, prefix="/api/db-connections", tags=["Database Connections"])

    # Include API Push Ingestion Router (/api/ingest)
    from app.api.api_ingest import router as api_ingest_router
    app.include_router(api_ingest_router, prefix="/api/ingest", tags=["API Ingestion"])

    # Include API Keys Management Router (/api/api-keys)
    from app.api.api_keys import router as api_keys_router
    app.include_router(api_keys_router, prefix="/api/api-keys", tags=["API Keys"])

    # Include Customer Analytics Dashboard Router (/api/dashboard)
    from app.api.dashboard import router as dashboard_router
    app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])

    # Include Pipeline Health & Recovery Router (/api/pipeline)
    from app.api.pipeline_health import router as pipeline_health_router
    app.include_router(pipeline_health_router, prefix="/api/pipeline", tags=["Pipeline Health"])

    # Include Dashboard Data Export Router (/api/export)
    from app.api.export import router as export_router
    app.include_router(export_router, prefix="/api/export", tags=["Export"])

    # Include Notifications Router (/api/notifications)
    from app.api.notifications import router as notifications_router
    app.include_router(notifications_router, prefix="/api/notifications", tags=["Notifications"])

    # Include Data Submission History Router (/api/history)
    from app.api.history import router as history_router
    app.include_router(history_router, prefix="/api/history", tags=["History"])

    # Include Support Messages Router (/api/support)
    from app.api.support import router as support_router
    app.include_router(support_router, prefix="/api/support", tags=["Support"])

    # Include Admin Oversight Router (/api/oversight)
    from app.api.oversight import router as oversight_router
    app.include_router(oversight_router, prefix="/api/oversight", tags=["Admin Oversight"])

    # Include Tenants Router (/api/tenants)
    from app.api.tenants import router as tenants_router
    app.include_router(tenants_router, prefix="/api/tenants", tags=["Tenants"])

    # Include Team Members Router (/api/team-members)
    from app.api.team import router as team_router
    app.include_router(team_router, prefix="/api/team-members", tags=["Team Members"])

    # Include Versioned API Routers
    app.include_router(api_router, prefix=settings.API_V1_STR)

    # Register Global Exception Handlers
    @app.exception_handler(HeliosException)
    async def helios_exception_handler(request: Request, exc: HeliosException) -> JSONResponse:
        """Global handler transforming Helios domain exceptions into standardized JSON responses."""
        logger.warning(
            "Helios [%s] error on %s %s: %s (status: %d)",
            exc.__class__.__name__,
            request.method,
            request.url.path,
            exc.message,
            exc.status_code,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.message,
                "detail": exc.message,
                "details": exc.details,
                "error_type": exc.__class__.__name__,
            },
        )

    return app


app = create_application()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.is_development)
