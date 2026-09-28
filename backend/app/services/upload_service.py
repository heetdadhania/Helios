import csv
import io
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import openpyxl
from fastapi import HTTPException, UploadFile, status

from app.repositories.upload_repository import UploadRepository
from app.schemas.auth import UserOut
from app.schemas.upload import UploadResponse, UploadStatusOut

logger = logging.getLogger("helios.upload")

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".csv", ".xlsx"}
VOLUME_BASE_PATH = "/Volumes/helios/bronze/uploads"


class UploadService:
    """Service handling file upload validation, persistence, and status simplification."""

    @staticmethod
    def _validate_file_metadata(filename: Optional[str], size: int) -> str:
        """Validate filename presence, extension, and non-empty byte size."""
        if not filename or not filename.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename cannot be empty.",
            )

        _, ext = os.path.splitext(filename.lower())
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{ext}'. Only .csv and .xlsx files are permitted.",
            )

        if size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty. Uploaded file must contain data.",
            )

        if size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File size exceeds the maximum permitted limit of 10MB.",
            )

        return ext

    @staticmethod
    def _validate_csv_content(content: bytes) -> None:
        """Verify CSV contains at least one non-empty header and one non-empty data row."""
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text = content.decode("latin-1")
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to decode CSV content. Ensure the file uses UTF-8 encoding.",
                ) from exc

        reader = csv.reader(io.StringIO(text))
        non_empty_rows = [
            row for row in reader if any(cell.strip() for cell in row)
        ]

        if not non_empty_rows:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty.",
            )

        if len(non_empty_rows) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File contains only headers with no data rows. At least one data row is required.",
            )

    @staticmethod
    def _validate_xlsx_content(content: bytes) -> None:
        """Verify Excel workbook contains at least one header row and one data row."""
        try:
            workbook = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
            sheet = workbook.active
            if sheet is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Excel file does not contain any active worksheet.",
                )

            non_empty_count = 0
            for row in sheet.iter_rows(values_only=True):
                if any(cell is not None and str(cell).strip() != "" for cell in row):
                    non_empty_count += 1
                    if non_empty_count >= 2:
                        break

            workbook.close()
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid or corrupted Excel file: {str(exc)}",
            ) from exc

        if non_empty_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty.",
            )

        if non_empty_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File contains only headers with no data rows. At least one data row is required.",
            )

    @classmethod
    def validate_file(cls, filename: Optional[str], content: bytes) -> None:
        """Run complete validation suite for type, size, emptiness, and header-only rows."""
        ext = cls._validate_file_metadata(filename, len(content))
        if ext == ".csv":
            cls._validate_csv_content(content)
        elif ext == ".xlsx":
            cls._validate_xlsx_content(content)

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Sanitize original filename to prevent path traversal and shell issues."""
        base_name = os.path.basename(filename)
        cleaned = re.sub(r"[^a-zA-Z0-9_.-]", "_", base_name)
        return cleaned or "upload.data"

    @classmethod
    def save_file(
        cls,
        content: bytes,
        tenant_id: int,
        batch_id: str,
        original_filename: str,
    ) -> str:
        """
        Save file to Databricks Unity Catalog Volume path.
        Target format: /Volumes/helios/bronze/uploads/{tenant_id}/{batch_id}/{filename}
        """
        safe_filename = cls._sanitize_filename(original_filename)
        volume_dir_str = f"{VOLUME_BASE_PATH}/{tenant_id}/{batch_id}"
        volume_path_str = f"{volume_dir_str}/{safe_filename}"

        try:
            target_dir = Path(volume_dir_str)
            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / safe_filename
            target_file.write_bytes(content)
        except OSError:
            # Fallback for environments with restricted root drive permissions
            fallback_dir = Path("storage") / "volumes" / "helios" / "bronze" / "uploads" / str(tenant_id) / batch_id
            fallback_dir.mkdir(parents=True, exist_ok=True)
            fallback_file = fallback_dir / safe_filename
            fallback_file.write_bytes(content)

        return volume_path_str

    @classmethod
    async def process_upload(
        cls,
        file: UploadFile,
        current_user: UserOut,
        repo: UploadRepository,
        tenant_id: Optional[int] = None,
    ) -> UploadResponse:
        """
        Validate file, store in Unity Catalog Volume, generate batch UUID, and persist tracking rows.
        Records the acting user (uploaded_by) for audit accountability trail.
        """
        target_tenant_id = tenant_id if tenant_id is not None else current_user.tenant_id
        if target_tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target tenant ID is required.",
            )

        logger.info(
            "Processing upload for tenant %s by user %s (role=%s, file=%s)",
            target_tenant_id,
            current_user.id,
            current_user.role,
            file.filename,
        )

        content = await file.read()
        cls.validate_file(file.filename, content)

        batch_id = str(uuid.uuid4())
        volume_file_path = cls.save_file(
            content=content,
            tenant_id=target_tenant_id,
            batch_id=batch_id,
            original_filename=file.filename or "upload.data",
        )

        upload_record = repo.create_upload(
            tenant_id=target_tenant_id,
            source_type="upload",
            file_name=cls._sanitize_filename(file.filename or "upload.data"),
            file_path=volume_file_path,
            uploaded_by=current_user.id,
            status="pending",
        )

        repo.create_pipeline_status(
            batch_id=batch_id,
            tenant_id=target_tenant_id,
            upload_id=int(upload_record["upload_id"]),
            stage="received",
            status="ingested",
        )

        try:
            from app.services.notification_service import NotificationService
            NotificationService.notify_upload_received(
                tenant_id=target_tenant_id,
                batch_id=batch_id,
                user_id=current_user.id,
                source_type="upload",
                cursor=repo.cursor,
            )
        except Exception as notif_err:
            logger.warning("Failed to dispatch upload_received notification: %s", notif_err)

        return UploadResponse(
            upload_id=int(upload_record["upload_id"]),
            batch_id=batch_id,
            status=str(upload_record["status"]),
        )

    @staticmethod
    def simplify_status(raw_status: Optional[str]) -> Tuple[str, str]:
        """
        Map internal technical pipeline states to plain-language, SMB-owner-safe status and stage.
        Never exposes internal stage names, error stack traces, or pipeline terminology.
        """
        normalized = (raw_status or "").strip().lower()

        if normalized in ("failed", "rejected", "error"):
            return "Failed", "Failed — please check your file and try again"
        elif normalized in ("success", "completed", "ready", "awaiting_confirmation"):
            return "Ready", "Ready"
        else:
            return "Processing", "Processing"

    @classmethod
    def get_upload_status(
        cls,
        upload_id: int,
        current_user: UserOut,
        repo: UploadRepository,
        tenant_id: Optional[int] = None,
    ) -> UploadStatusOut:
        """
        Retrieve simplified plain-language status for an SMB Owner.
        """
        effective_tenant_id = tenant_id if tenant_id is not None else current_user.tenant_id
        if effective_tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account does not have an assigned tenant ID.",
            )

        upload_record = repo.get_by_id(upload_id=upload_id, tenant_id=effective_tenant_id)
        if not upload_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload with ID {upload_id} not found.",
            )

        pipeline_record = repo.get_pipeline_status_by_upload_id(
            upload_id=upload_id,
            tenant_id=effective_tenant_id,
        )

        if pipeline_record:
            batch_id = str(pipeline_record["batch_id"])
            raw_status = str(pipeline_record["status"])
            updated_at = pipeline_record.get("updated_at") or datetime.now(timezone.utc)
        else:
            batch_id = f"batch-pending-{upload_id}"
            raw_status = str(upload_record.get("status", "pending"))
            updated_at = upload_record.get("uploaded_at") or datetime.now(timezone.utc)

        simplified_stage, simplified_status = cls.simplify_status(raw_status)

        return UploadStatusOut(
            batch_id=batch_id,
            stage=simplified_stage,
            status=simplified_status,
            updated_at=updated_at,
        )
