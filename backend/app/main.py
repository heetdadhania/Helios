import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from app.api.v1.api import api_router
from app.core.config import settings

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

    # Include Ingestion Uploads Router (/api/uploads)
    from app.api.uploads import router as uploads_router
    app.include_router(uploads_router, prefix="/api/uploads", tags=["Uploads"])

    # Include Versioned API Routers
    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.get("/", include_in_schema=False)
    def root_redirect() -> RedirectResponse:
        """Redirect root requests to interactive Swagger documentation."""
        return RedirectResponse(url="/docs", status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    return app


app = create_application()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.is_development)
