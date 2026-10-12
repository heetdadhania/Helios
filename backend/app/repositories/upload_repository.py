from typing import Any, Dict, Optional
from databricks.sql.client import Cursor
from app.core.config import settings
from app.repositories.base import BaseRepository


class UploadRepository(BaseRepository):
    """
    Data access repository for file uploads and pipeline tracking tables in Databricks Unity Catalog.
    
    Interacts with platform.pending_uploads and platform.pipeline_status Delta tables.
    """

    def __init__(self, cursor: Cursor, catalog: Optional[str] = None) -> None:
        super().__init__(cursor)
        self.catalog = catalog or settings.DATABRICKS_CATALOG
        self.pending_table = f"`{self.catalog}`.`platform`.`pending_uploads`"
        self.pipeline_table = f"`{self.catalog}`.`platform`.`pipeline_status`"

    def create_upload(
        self,
        tenant_id: int,
        source_type: str,
        file_name: str,
        file_path: str,
        uploaded_by: Optional[int] = None,
        status: str = "pending",
        file_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Insert a new upload record into platform.pending_uploads and return the persisted record.
        """
        insert_query = f"""
            INSERT INTO {self.pending_table} (
                tenant_id, source_type, file_name, file_path, uploaded_by, status, file_hash, uploaded_at
            )
            VALUES (
                :tenant_id, :source_type, :file_name, :file_path, :uploaded_by, :status, :file_hash, current_timestamp()
            )
        """
        params = {
            "tenant_id": tenant_id,
            "source_type": source_type,
            "file_name": file_name,
            "file_path": file_path,
            "uploaded_by": uploaded_by,
            "status": status,
            "file_hash": file_hash,
        }
        self.execute_non_query(insert_query, params)

        select_query = f"""
            SELECT upload_id, tenant_id, source_type, file_name, file_path, uploaded_by, uploaded_at, status, file_hash
            FROM {self.pending_table}
            WHERE tenant_id = :tenant_id AND file_path = :file_path
            ORDER BY upload_id DESC
            LIMIT 1
        """
        record = self.execute_single(select_query, {"tenant_id": tenant_id, "file_path": file_path})
        if not record:
            raise RuntimeError(f"Failed to retrieve newly created upload record for {file_name}")
        return record

    def get_by_id(self, upload_id: int, tenant_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch a pending upload record by upload_id, optionally enforcing tenant isolation.
        """
        if tenant_id is not None:
            query = f"""
                SELECT upload_id, tenant_id, source_type, file_name, file_path, uploaded_by, uploaded_at, status
                FROM {self.pending_table}
                WHERE upload_id = :upload_id AND tenant_id = :tenant_id
                LIMIT 1
            """
            return self.execute_single(query, {"upload_id": upload_id, "tenant_id": tenant_id})

        query = f"""
            SELECT upload_id, tenant_id, source_type, file_name, file_path, uploaded_by, uploaded_at, status
            FROM {self.pending_table}
            WHERE upload_id = :upload_id
            LIMIT 1
        """
        return self.execute_single(query, {"upload_id": upload_id})

    def update_status(
        self,
        upload_id: int,
        status: str,
        tenant_id: Optional[int] = None,
    ) -> None:
        """
        Update the lifecycle status of an upload record in platform.pending_uploads.
        """
        if tenant_id is not None:
            query = f"""
                UPDATE {self.pending_table}
                SET status = :status
                WHERE upload_id = :upload_id AND tenant_id = :tenant_id
            """
            self.execute_non_query(query, {"upload_id": upload_id, "tenant_id": tenant_id, "status": status})
        else:
            query = f"""
                UPDATE {self.pending_table}
                SET status = :status
                WHERE upload_id = :upload_id
            """
            self.execute_non_query(query, {"upload_id": upload_id, "status": status})

    def create_pipeline_status(
        self,
        batch_id: str,
        tenant_id: int,
        upload_id: int,
        stage: str = "received",
        status: str = "ingested",
        error_message: Optional[str] = None,
    ) -> None:
        """
        Insert an initial tracking row into platform.pipeline_status for this batch execution.
        """
        query = f"""
            INSERT INTO {self.pipeline_table} (
                batch_id, tenant_id, upload_id, stage, status, error_message, created_at, updated_at
            )
            VALUES (
                :batch_id, :tenant_id, :upload_id, :stage, :status, :error_message, current_timestamp(), current_timestamp()
            )
        """
        self.execute_non_query(
            query,
            {
                "batch_id": batch_id,
                "tenant_id": tenant_id,
                "upload_id": upload_id,
                "stage": stage,
                "status": status,
                "error_message": error_message,
            },
        )

    def get_pipeline_status_by_upload_id(
        self,
        upload_id: int,
        tenant_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch the latest pipeline execution status record for an upload ID.
        """
        if tenant_id is not None:
            query = f"""
                SELECT batch_id, tenant_id, upload_id, stage, status, error_message, created_at, updated_at
                FROM {self.pipeline_table}
                WHERE upload_id = :upload_id AND tenant_id = :tenant_id
                ORDER BY updated_at DESC
                LIMIT 1
            """
            return self.execute_single(query, {"upload_id": upload_id, "tenant_id": tenant_id})

        query = f"""
            SELECT batch_id, tenant_id, upload_id, stage, status, error_message, created_at, updated_at
            FROM {self.pipeline_table}
            WHERE upload_id = :upload_id
            ORDER BY updated_at DESC
            LIMIT 1
        """
        return self.execute_single(query, {"upload_id": upload_id})
