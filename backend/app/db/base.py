import logging
import os
import queue
import threading
import time
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


class PooledConnection:
    """
    Transparent proxy around a Databricks SQL Connection.
    Intercepts .close() to return the underlying connection to the pool
    rather than destroying the underlying Databricks session.
    """

    def __init__(self, raw_conn: Connection, pool: "DatabricksConnectionPool") -> None:
        self._raw_conn = raw_conn
        self._pool = pool
        self._is_closed = False
        self._invalidated = False

    def close(self, force: bool = False) -> None:
        """Return to pool on close unless force=True or marked invalidated."""
        if not self._is_closed:
            self._is_closed = True
            if force or self._invalidated:
                self._pool.discard(self._raw_conn)
            else:
                self._pool.release(self._raw_conn)

    def invalidate(self) -> None:
        """Mark connection as unhealthy so it will be discarded upon release."""
        self._invalidated = True

    def cursor(self, *args: Any, **kwargs: Any) -> Cursor:
        """Create and return an active cursor on the underlying connection."""
        if self._is_closed:
            raise RuntimeError("Cannot open cursor on a closed pooled connection.")
        return self._raw_conn.cursor(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._raw_conn, name)

    def __enter__(self) -> "PooledConnection":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            self.invalidate()
        self.close()


class DatabricksConnectionPool:
    """
    Thread-safe connection pool for Databricks SQL endpoint.
    Maintains active connections using a LIFO queue to keep recent connections warm
    and eliminate repeated TCP/TLS handshake overhead across dashboard requests.
    """

    def __init__(
        self,
        max_size: int = 10,
        max_idle_seconds: float = 300.0,
    ) -> None:
        self.max_size = max_size
        self.max_idle_seconds = max_idle_seconds
        self._pool: queue.LifoQueue[Connection] = queue.LifoQueue(maxsize=max_size)
        self._lock = threading.Lock()
        self._created_count = 0

    def _create_raw_connection(
        self,
        catalog: Optional[str] = None,
        schema: Optional[str] = None,
        max_retries: int = 3,
        base_backoff: float = 1.0,
    ) -> Connection:
        """Establish a genuine physical connection to the Databricks SQL warehouse."""
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
                conn = sql.connect(
                    server_hostname=settings.DATABRICKS_SERVER_HOSTNAME,
                    http_path=settings.DATABRICKS_HTTP_PATH,
                    access_token=settings.DATABRICKS_TOKEN,
                    catalog=target_catalog,
                    schema=target_schema,
                )
                conn._last_used_at = time.time()
                return conn
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

    def acquire(
        self,
        catalog: Optional[str] = None,
        schema: Optional[str] = None,
        timeout: float = 10.0,
        max_retries: int = 3,
        base_backoff: float = 1.0,
    ) -> PooledConnection:
        """
        Acquire a connection from the pool. Reuses healthy warm connections or creates
        a new one if pool has capacity.
        """
        while True:
            try:
                conn = self._pool.get_nowait()
                is_open = getattr(conn, "open", True)
                last_used = getattr(conn, "_last_used_at", 0)
                is_fresh = (time.time() - last_used) <= self.max_idle_seconds

                if is_open and is_fresh:
                    conn._last_used_at = time.time()
                    return PooledConnection(conn, self)
                else:
                    logger.info("Discarding expired or closed Databricks connection from pool.")
                    self.discard(conn)
            except queue.Empty:
                break

        # Pool is empty: create a new connection if under limit, or wait
        with self._lock:
            if self._created_count < self.max_size:
                raw_conn = self._create_raw_connection(
                    catalog=catalog,
                    schema=schema,
                    max_retries=max_retries,
                    base_backoff=base_backoff,
                )
                self._created_count += 1
                return PooledConnection(raw_conn, self)

        # Wait for an available connection from the pool up to timeout
        try:
            conn = self._pool.get(timeout=timeout)
            conn._last_used_at = time.time()
            return PooledConnection(conn, self)
        except queue.Empty:
            # Fall back to creating a temporary connection
            raw_conn = self._create_raw_connection(
                catalog=catalog,
                schema=schema,
                max_retries=max_retries,
                base_backoff=base_backoff,
            )
            return PooledConnection(raw_conn, self)

    def release(self, raw_conn: Connection) -> None:
        """Return a healthy raw connection to the pool."""
        if getattr(raw_conn, "open", False):
            raw_conn._last_used_at = time.time()
            try:
                self._pool.put_nowait(raw_conn)
                return
            except queue.Full:
                pass
        self.discard(raw_conn)

    def discard(self, raw_conn: Connection) -> None:
        """Close and discard an unhealthy connection, updating active count."""
        with self._lock:
            if self._created_count > 0:
                self._created_count -= 1
        try:
            if hasattr(raw_conn, "close"):
                raw_conn.close()
        except Exception as exc:
            logger.debug("Error closing discarded connection: %s", exc)

    def close_all(self) -> None:
        """Close all idle connections in the pool."""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                try:
                    conn.close()
                except Exception:
                    pass
            except queue.Empty:
                break
        with self._lock:
            self._created_count = 0


_global_pool: Optional[DatabricksConnectionPool] = None
_pool_lock = threading.Lock()


def get_connection_pool() -> DatabricksConnectionPool:
    """Retrieve or initialize the singleton Databricks connection pool."""
    global _global_pool
    if _global_pool is None:
        with _pool_lock:
            if _global_pool is None:
                pool_size = int(os.getenv("DATABRICKS_POOL_SIZE", "10"))
                max_idle = float(os.getenv("DATABRICKS_POOL_MAX_IDLE_SECONDS", "300"))
                _global_pool = DatabricksConnectionPool(max_size=pool_size, max_idle_seconds=max_idle)
    return _global_pool


def close_connection_pool() -> None:
    """Tear down and close all active connections in the singleton pool."""
    global _global_pool
    if _global_pool is not None:
        with _pool_lock:
            if _global_pool is not None:
                _global_pool.close_all()
                _global_pool = None


def get_databricks_connection(
    catalog: Optional[str] = None,
    schema: Optional[str] = None,
    max_retries: int = 3,
    base_backoff: float = 1.0,
    use_pool: bool = True,
) -> Connection:
    """
    Establish and return a connection to Databricks SQL endpoint using Unity Catalog.
    
    When use_pool=True (default), acquires a pooled connection to avoid redundant TLS handshakes.
    Implements retry-with-backoff to absorb warehouse cold starts and transient connection delays.
    """
    if use_pool and sql is not None:
        pool = get_connection_pool()
        return pool.acquire(
            catalog=catalog,
            schema=schema,
            max_retries=max_retries,
            base_backoff=base_backoff,
        )

    # Fall back to direct unpooled connection creation
    pool = get_connection_pool()
    return pool._create_raw_connection(
        catalog=catalog,
        schema=schema,
        max_retries=max_retries,
        base_backoff=base_backoff,
    )


def release_databricks_connection(conn: Connection) -> None:
    """Safely return connection to the pool or close it."""
    try:
        conn.close()
    except Exception as exc:
        logger.warning("Error releasing Databricks connection: %s", exc)


@contextmanager
def databricks_cursor(
    connection: Optional[Connection] = None,
    catalog: Optional[str] = None,
    schema: Optional[str] = None,
    use_pool: bool = True,
) -> Generator[Cursor, None, None]:
    """
    Context manager yielding a Databricks SQL cursor.
    
    Reuses pooled connections by default, safely closing cursor and returning connection to pool.
    """
    owned_conn = False
    conn = connection
    cursor = None
    try:
        if conn is None:
            conn = get_databricks_connection(catalog=catalog, schema=schema, use_pool=use_pool)
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
