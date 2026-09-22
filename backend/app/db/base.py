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
) -> Connection:
    """
    Establish and return a new connection to Databricks SQL endpoint using Unity Catalog.
    
    Reads credentials and endpoint details directly from application settings.
    """
    from app.core.config import settings

    if sql is None:
        raise RuntimeError(
            "databricks-sql-connector is not installed. Run 'pip install -r requirements.txt' to install it."
        )

    target_catalog = catalog or settings.DATABRICKS_CATALOG
    target_schema = schema or settings.DATABRICKS_SCHEMA

    return sql.connect(
        server_hostname=settings.DATABRICKS_SERVER_HOSTNAME,
        http_path=settings.DATABRICKS_HTTP_PATH,
        access_token=settings.DATABRICKS_TOKEN,
        catalog=target_catalog,
        schema=target_schema,
    )


@contextmanager
def databricks_cursor(
    connection: Optional[Connection] = None,
    catalog: Optional[str] = None,
    schema: Optional[str] = None,
) -> Generator[Cursor, None, None]:
    """
    Context manager yielding a Databricks SQL cursor.
    
    Closes cursor and connection automatically upon exiting the context.
    """
    owned_conn = False
    conn = connection
    if conn is None:
        conn = get_databricks_connection(catalog=catalog, schema=schema)
        owned_conn = True

    cursor = conn.cursor()
    try:
        yield cursor
    finally:
        try:
            cursor.close()
        except Exception as exc:
            logger.warning("Error closing Databricks cursor: %s", exc)
        if owned_conn:
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
