from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables using Pydantic Settings."""

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "../backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Project Information
    PROJECT_NAME: str = "Helios Multi-Tenant Data Platform"
    ENVIRONMENT: str = "development"
    API_V1_STR: str = "/api/v1"

    # Security & Tokens
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    CREDENTIAL_ENCRYPTION_KEY: str

    # Databricks SQL Connector Config (Free Edition / Unity Catalog)
    DATABRICKS_SERVER_HOSTNAME: str
    DATABRICKS_HTTP_PATH: str
    DATABRICKS_TOKEN: str
    DATABRICKS_CATALOG: str = "helios_catalog"
    DATABRICKS_SCHEMA: str = "default"

    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse comma-separated string or preserve list of allowed CORS origins."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(f"Invalid CORS origins value: {v}")

    @property
    def is_development(self) -> bool:
        """Check if application is running in development mode."""
        return self.ENVIRONMENT.lower() == "development"


settings = Settings()
