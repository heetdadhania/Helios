import base64
import csv
import io
import logging
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional, Tuple

import mysql.connector
import psycopg2
import pymssql
from databricks.sdk import WorkspaceClient
from fastapi import HTTPException, status

from app.core.config import settings
from app.repositories.db_connection_repository import DbConnectionRepository
from app.repositories.upload_repository import UploadRepository
from app.schemas.db_connection import (
    DbConnectionCreate,
    DbConnectionOut,
    DbConnectionTestResult,
)
from app.schemas.upload import UploadResponse
from app.services.upload_service import UploadService

logger = logging.getLogger("helios.db_connection")


def sanitize_error_message(exc: Exception, secret: str) -> str:
    """Remove raw credentials from exception strings to prevent leakage."""
    msg = str(exc)
    if secret and secret in msg:
        msg = msg.replace(secret, "******")
    return msg


def decode_secret_value(raw_val: str) -> str:
    """Decode Databricks Secrets base64 string or return plain string."""
    try:
        decoded_bytes = base64.b64decode(raw_val.encode("utf-8"), validate=True)
        return decoded_bytes.decode("utf-8")
    except Exception:
        return raw_val


def get_databricks_workspace_client() -> WorkspaceClient:
    """Instantiate Databricks SDK WorkspaceClient using app settings."""
    return WorkspaceClient(
        host=settings.DATABRICKS_SERVER_HOSTNAME,
        token=settings.DATABRICKS_TOKEN,
    )


class DbConnectionService:
    """Service handling multi-engine DB connections, secrets storage, and Bronze extraction."""

    @classmethod
    @contextmanager
    def open_external_connection(
        cls,
        db_type: str,
        host: str,
        port: int,
        database_name: str,
        username: str,
        password: str,
    ) -> Generator[Any, None, None]:
        """Establish TLS-enabled connection to external DB and ensure cleanup."""
        engine = db_type.strip().lower()
        conn = None
        try:
            if engine == "mysql":
                conn = mysql.connector.connect(
                    host=host,
                    port=port,
                    database=database_name,
                    user=username,
                    password=password,
                    connection_timeout=10,
                    ssl_disabled=False,
                )
            elif engine == "postgresql":
                conn = psycopg2.connect(
                    host=host,
                    port=port,
                    dbname=database_name,
                    user=username,
                    password=password,
                    connect_timeout=10,
                    sslmode="prefer",
                )
            elif engine == "sqlserver":
                conn = pymssql.connect(
                    server=host,
                    port=str(port),
                    database=database_name,
                    user=username,
                    password=password,
                    timeout=10,
                    login_timeout=10,
                    encryption=True,
                )
            else:
                raise ValueError(f"Unsupported database engine '{db_type}'. Must be mysql, postgresql, or sqlserver.")

            yield conn
        finally:
            if conn:
                try:
                    conn.close()
                except Exception as exc:
                    logger.warning("Error closing external DB connection: %s", exc)

    @classmethod
    def test_connection(
        cls,
        db_type: str,
        host: str,
        port: int,
        database_name: str,
        username: str,
        password: str,
    ) -> DbConnectionTestResult:
        """Attempt connection and run trivial SELECT 1 query without persisting password."""
        logger.info("Testing connection for type '%s' at %s:%d/%s", db_type, host, port, database_name)
        try:
            with cls.open_external_connection(
                db_type=db_type,
                host=host,
                port=port,
                database_name=database_name,
                username=username,
                password=password,
            ) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                res = cursor.fetchone()
                cursor.close()
                if res is None:
                    return DbConnectionTestResult(
                        success=False,
                        message="Connection test query (SELECT 1) returned no rows.",
                    )
            return DbConnectionTestResult(
                success=True,
                message=f"Successfully connected to {db_type} database and verified credentials.",
            )
        except Exception as exc:
            safe_msg = sanitize_error_message(exc, password)
            logger.error("Database connection test failed for %s:%d: %s", host, port, safe_msg)
            return DbConnectionTestResult(
                success=False,
                message=f"Connection test failed: {safe_msg}",
            )

    @staticmethod
    def _store_credential_in_secrets(
        tenant_id: int,
        password: str,
        client: Optional[WorkspaceClient] = None,
    ) -> str:
        """Send raw password to Databricks Secrets and return scope:key reference."""
        scope = f"helios_tenant_{tenant_id}"
        key = f"conn_{uuid.uuid4().hex[:16]}"
        ws = client or get_databricks_workspace_client()

        try:
            ws.secrets.create_scope(scope=scope)
        except Exception:
            pass  # Scope already exists or created by admin

        ws.secrets.put_secret(scope=scope, key=key, string_value=password)
        return f"{scope}:{key}"

    @classmethod
    def save_connection(
        cls,
        conn_in: DbConnectionCreate,
        tenant_id: int,
        repo: DbConnectionRepository,
        secrets_client: Optional[WorkspaceClient] = None,
    ) -> DbConnectionOut:
        """Save connection metadata in platform.db_connections and credential in Databricks Secrets."""
        credential_ref = cls._store_credential_in_secrets(
            tenant_id=tenant_id,
            password=conn_in.password,
            client=secrets_client,
        )

        record = repo.create(
            tenant_id=tenant_id,
            db_type=conn_in.db_type,
            host=conn_in.host,
            port=conn_in.port,
            database_name=conn_in.database_name,
            username=conn_in.username,
            encrypted_credential_ref=credential_ref,
            table_or_query=conn_in.table_or_query,
            is_active=conn_in.is_active,
        )

        return DbConnectionOut(
            connection_id=int(record["connection_id"]),
            tenant_id=int(record["tenant_id"]),
            db_type=str(record["db_type"]),
            host=str(record["host"]),
            port=int(record["port"]),
            database_name=str(record["database_name"]),
            username=str(record["username"]),
            table_or_query=str(record["table_or_query"]),
            last_synced_at=record.get("last_synced_at"),
            created_at=record.get("created_at"),
            is_active=bool(record.get("is_active", True)),
        )

    @staticmethod
    def _retrieve_credential_from_secrets(
        credential_ref: str,
        client: Optional[WorkspaceClient] = None,
    ) -> str:
        """Fetch password ephemerally from Databricks Secrets. Never caches value."""
        if ":" not in credential_ref:
            raise ValueError("Malformed Databricks secret reference. Expected format 'scope:key'.")

        scope, key = credential_ref.split(":", 1)
        ws = client or get_databricks_workspace_client()
        resp = ws.secrets.get_secret(scope=scope, key=key)
        if not resp or not resp.value:
            raise RuntimeError(f"Databricks secret '{credential_ref}' not found or empty.")

        return decode_secret_value(resp.value)

    @staticmethod
    def _build_select_query(db_type: str, table_or_query: str) -> str:
        """Construct valid query from raw table name or custom SELECT expression."""
        trimmed = table_or_query.strip()
        upper = trimmed.upper()
        if upper.startswith("SELECT") or upper.startswith("WITH"):
            return trimmed

        clean_table = trimmed.replace(";", "").replace("--", "").strip()
        engine = db_type.strip().lower()
        if engine == "mysql":
            return f"SELECT * FROM `{clean_table}`"
        elif engine == "postgresql":
            return f'SELECT * FROM "{clean_table}"'
        elif engine == "sqlserver":
            return f"SELECT * FROM [{clean_table}]"
        return f"SELECT * FROM {clean_table}"

    @classmethod
    def _extract_rows_to_csv(
        cls,
        conn: Any,
        db_type: str,
        table_or_query: str,
    ) -> Tuple[bytes, int]:
        """Execute extraction query and serialize results to CSV bytes."""
        sql = cls._build_select_query(db_type, table_or_query)
        cursor = conn.cursor()
        cursor.execute(sql)

        description = cursor.description
        if not description:
            cursor.close()
            return b"", 0

        columns = [col[0] for col in description]
        rows = cursor.fetchall()
        cursor.close()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        for r in rows:
            if isinstance(r, dict):
                writer.writerow([r.get(c) for c in columns])
            else:
                writer.writerow(list(r))

        return output.getvalue().encode("utf-8"), len(rows)

    @classmethod
    def sync_now(
        cls,
        connection_id: int,
        tenant_id: int,
        user_id: Optional[int],
        repo: DbConnectionRepository,
        upload_repo: UploadRepository,
        secrets_client: Optional[WorkspaceClient] = None,
    ) -> UploadResponse:
        """Fetch password ephemerally, pull table/query rows, and ingest into Bronze."""
        conn_record = repo.get_by_id(connection_id=connection_id, tenant_id=tenant_id)
        if not conn_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Database connection {connection_id} not found for this tenant.",
            )

        raw_password = cls._retrieve_credential_from_secrets(
            credential_ref=str(conn_record["encrypted_credential_ref"]),
            client=secrets_client,
        )

        try:
            with cls.open_external_connection(
                db_type=str(conn_record["db_type"]),
                host=str(conn_record["host"]),
                port=int(conn_record["port"]),
                database_name=str(conn_record["database_name"]),
                username=str(conn_record["username"]),
                password=raw_password,
            ) as ext_conn:
                csv_bytes, row_count = cls._extract_rows_to_csv(
                    conn=ext_conn,
                    db_type=str(conn_record["db_type"]),
                    table_or_query=str(conn_record["table_or_query"]),
                )
        finally:
            raw_password = ""  # Immediate cleanup from memory

        batch_id = str(uuid.uuid4())
        ts = int(datetime.now(timezone.utc).timestamp())
        file_name = f"db_sync_{connection_id}_{ts}.csv"

        volume_path = UploadService.save_file(
            content=csv_bytes,
            tenant_id=tenant_id,
            batch_id=batch_id,
            original_filename=file_name,
        )

        upload_record = upload_repo.create_upload(
            tenant_id=tenant_id,
            source_type="db_connection",
            file_name=file_name,
            file_path=volume_path,
            uploaded_by=user_id,
            status="pending",
        )

        upload_repo.create_pipeline_status(
            batch_id=batch_id,
            tenant_id=tenant_id,
            upload_id=int(upload_record["upload_id"]),
            stage="received",
            status="ingested",
        )

        repo.update_last_synced(connection_id=connection_id, tenant_id=tenant_id)

        return UploadResponse(
            upload_id=int(upload_record["upload_id"]),
            batch_id=batch_id,
            status=str(upload_record["status"]),
        )
