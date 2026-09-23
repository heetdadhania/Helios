import csv
import io
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import HTTPException, status

from app.repositories.upload_repository import UploadRepository
from app.schemas.api_ingest import ApiIngestResponse
from app.services.upload_service import UploadService, MAX_FILE_SIZE_BYTES

logger = logging.getLogger("helios.api_ingest")


class ApiIngestService:
    """Service validating programmatic API push records and landing them in Bronze storage."""

    @staticmethod
    def validate_payload_shape(records: List[Dict[str, Any]]) -> None:
        """Verify records list is non-empty, properly structured, and contains scalar/dict values."""
        if not records:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payload must contain at least one record in the 'records' array.",
            )

        if len(records) > 10000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payload exceeds maximum limit of 10,000 records per push.",
            )

        for idx, rec in enumerate(records):
            if not isinstance(rec, dict) or not rec:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Record at index {idx} is invalid. Each item must be a non-empty JSON object.",
                )

    @classmethod
    def _convert_records_to_csv(cls, records: List[Dict[str, Any]]) -> bytes:
        """Serialize JSON record dictionaries to CSV byte content."""
        columns: List[str] = []
        for rec in records:
            for key in rec.keys():
                k_str = str(key)
                if k_str not in columns:
                    columns.append(k_str)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)

        for rec in records:
            row = [rec.get(col, "") for col in columns]
            writer.writerow(row)

        csv_bytes = output.getvalue().encode("utf-8")
        if len(csv_bytes) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payload byte size exceeds the maximum permitted limit of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB.",
            )

        return csv_bytes

    @classmethod
    def process_api_ingest(
        cls,
        records: List[Dict[str, Any]],
        tenant_id: int,
        upload_repo: UploadRepository,
    ) -> ApiIngestResponse:
        """Validate records, land in Unity Catalog Volume, and tag tracking rows as 'api_push'."""
        cls.validate_payload_shape(records)
        csv_bytes = cls._convert_records_to_csv(records)

        batch_id = str(uuid.uuid4())
        ts = int(datetime.now(timezone.utc).timestamp())
        file_name = f"api_push_{ts}.csv"

        volume_path = UploadService.save_file(
            content=csv_bytes,
            tenant_id=tenant_id,
            batch_id=batch_id,
            original_filename=file_name,
        )

        upload_record = upload_repo.create_upload(
            tenant_id=tenant_id,
            source_type="api_push",
            file_name=file_name,
            file_path=volume_path,
            uploaded_by=None,
            status="pending",
        )

        upload_repo.create_pipeline_status(
            batch_id=batch_id,
            tenant_id=tenant_id,
            upload_id=int(upload_record["upload_id"]),
            stage="received",
            status="ingested",
        )

        try:
            from app.services.notification_service import NotificationService
            NotificationService.notify_upload_received(
                tenant_id=tenant_id,
                batch_id=batch_id,
                user_id=None,
                source_type="api_push",
                cursor=upload_repo.cursor,
            )
        except Exception as notif_err:
            logger.warning("Failed to dispatch api_push notification: %s", notif_err)

        logger.info(
            "API Ingestion accepted for tenant %d: %d records, batch %s",
            tenant_id,
            len(records),
            batch_id,
        )

        return ApiIngestResponse(
            batch_id=batch_id,
            status="ingested",
            records_received=len(records),
        )
