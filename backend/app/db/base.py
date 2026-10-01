import logging
from contextlib import contextmanager
from typing import Any, Generator, Optional
try:
    from databricks import sql
    from databricks.sql.client import Connection, Cursor
except ImportError:
    sql = None  # type: ignore
    Connection = Any  # type: ignore
    Cursor = Any  # type: ignore
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy Declarative Base for ORM entity typing and schema definitions."""
    pass


def get_databricks_connection(
    catalog: Optional[str] = None,
    schema: Optional[str] = None,
    max_retries: int = 3,
    base_backoff: float = 1.0,
) -> Connection:
    """
    Establish and return a new connection to Databricks SQL endpoint using Unity Catalog.
    
    Reads credentials and endpoint details directly from application settings.
    Implements retry-with-backoff to absorb warehouse cold starts and transient connection delays.
    """
    import time
    from app.core.config import settings

    if sql is None:
        raise RuntimeError(
            "databricks-sql-connector is not installed. Run 'pip install -r requirements.txt' to install it."
        )

    target_catalog = catalog or settings.DATABRICKS_CATALOG
    target_schema = schema or settings.DATABRICKS_SCHEMA

    last_exception = None
    for attempt in range(1, max_retries + 1):
        try:
            return sql.connect(
                server_hostname=settings.DATABRICKS_SERVER_HOSTNAME,
                http_path=settings.DATABRICKS_HTTP_PATH,
                access_token=settings.DATABRICKS_TOKEN,
                catalog=target_catalog,
                schema=target_schema,
            )
        except Exception as exc:
            last_exception = exc
            if attempt < max_retries:
                backoff = base_backoff * (2 ** (attempt - 1))
                logger.warning(
                    "Databricks SQL connection attempt %d/%d failed: %s. Retrying in %.1fs...",
                    attempt,
                    max_retries,
                    exc,
                    backoff,
                )
                time.sleep(backoff)
            else:
                logger.error(
                    "All %d Databricks SQL connection attempts failed. Last error: %s",
                    max_retries,
                    exc,
                )
                raise exc

    if last_exception:
        raise last_exception
    raise RuntimeError("Failed to establish Databricks SQL connection.")


@contextmanager
def databricks_cursor(
    connection: Optional[Connection] = None,
    catalog: Optional[str] = None,
    schema: Optional[str] = None,
) -> Generator[Cursor, None, None]:
    """
    Context manager yielding a Databricks SQL cursor.
    
    Closes cursor and connection automatically upon exiting the context.
    Safely closes owned connections even if cursor initialization fails.
    """
    owned_conn = False
    conn = connection
    cursor = None
    try:
        if conn is None:
            conn = get_databricks_connection(catalog=catalog, schema=schema)
            owned_conn = True

        cursor = conn.cursor()
        yield cursor
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception as exc:
                logger.warning("Error closing Databricks cursor: %s", exc)
        if owned_conn and conn is not None:
            try:
                conn.close()
            except Exception as exc:
                logger.warning("Error closing Databricks connection: %s", exc)


def check_databricks_connection() -> bool:
    """Verify live connectivity to Databricks SQL endpoint by running a ping query."""
    try:
        with databricks_cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            return result is not None
    except Exception as exc:
        logger.error("Databricks connectivity check failed: %s", exc)
        return False
