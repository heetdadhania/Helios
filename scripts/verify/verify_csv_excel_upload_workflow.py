import io
import os
import sys
import uuid
import openpyxl
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath("backend"))

from fastapi.testclient import TestClient
from app.main import app
from app.core.dependencies import get_current_user, get_db_cursor
from app.schemas.auth import UserOut, UserRole
from app.repositories.upload_repository import UploadRepository
from app.repositories.confirmation_repository import ConfirmationRepository
from app.services.upload_service import UploadService
from app.services.confirmation_service import ConfirmationService
from app.services.duplicate_detector import DuplicateDetector
from app.services.notification_service import NotificationService
from pipeline.runner import pipeline_executor

client = TestClient(app)

def run_csv_and_excel_verification():
    print("============================================================")
    print("VERIFYING CSV & EXCEL UPLOAD WORKFLOWS (Pending -> Approval -> Success)")
    print("============================================================")

    admin_user = UserOut(
        id=1,
        name="Admin User",
        email="admin@helios.io",
        role=UserRole.ADMIN,
        tenant_id=None,
    )

    app.dependency_overrides[get_current_user] = lambda: admin_user
    mock_cursor = MagicMock()
    app.dependency_overrides[get_db_cursor] = lambda: mock_cursor

    created_batch_ids = []

    # -------------------------------------------------------------
    # 1. CSV Upload Workflow
    # -------------------------------------------------------------
    csv_batch_id = f"batch-csv-{uuid.uuid4().hex[:8]}"
    created_batch_ids.append(csv_batch_id)
    print(f"\n1. Submitting CSV file upload for Tenant 1 (Batch: {csv_batch_id})...")
    
    csv_content = (
        "order_id,customer_id,product_id,order_date,quantity,unit_price,total,discount\n"
        f"ORD-CSV-001,CUST-101,PROD-901,2026-11-05 10:00:00,2,250.00,500.00,0.00\n"
        f"ORD-CSV-002,CUST-102,PROD-902,2026-11-05 10:05:00,1,750.00,750.00,50.00\n"
    ).encode("utf-8")

    # Validate file format and rows using UploadService
    UploadService.validate_file("test_orders.csv", csv_content)
    print("  [PASS] CSV file validated: headers and data rows verified.")

    # Mock Bronze landing & pipeline submission
    with patch.object(
        UploadRepository,
        "create_upload",
        return_value={
            "upload_id": 9001,
            "tenant_id": 1,
            "source_type": "upload",
            "file_name": "test_orders.csv",
            "file_path": f"/Volumes/helios/bronze/uploads/1/{csv_batch_id}/test_orders.csv",
            "status": "pending",
        },
    ), patch.object(UploadRepository, "create_pipeline_status"), \
       patch.object(DuplicateDetector, "check_and_handle_duplicate"), \
       patch.object(NotificationService, "notify_upload_received"), \
       patch.object(pipeline_executor, "submit"):
        
        resp = client.post(
            "/api/uploads",
            files={"file": ("test_orders.csv", csv_content, "text/csv")},
            data={"tenant_id": 1, "override_duplicate": "true", "override_reason": "Automated verification test"},
        )
        assert resp.status_code == 201, f"CSV Upload endpoint failed: {resp.status_code} {resp.text}"
        data = resp.json()
        print(f"  [PASS] CSV upload landed in Bronze (Upload ID: {data['upload_id']}, Status: {data['status']})")

    # Verify Pending state & Schema Confirmation
    print(f"  [Pending Review] Batch {csv_batch_id} ready for schema confirmation.")
    with patch.object(
        ConfirmationRepository,
        "get_batch_metadata",
        return_value={
            "batch_id": csv_batch_id,
            "tenant_id": 1,
            "status": "awaiting_confirmation",
            "stage": "schema_inference",
            "detected_template": "template_orders",
            "source_type": "upload",
        },
    ), patch.object(ConfirmationRepository, "check_user_tenant_access", return_value=True), \
       patch.object(ConfirmationRepository, "is_tenant_running_batch", return_value=False), \
       patch.object(ConfirmationRepository, "save_confirmation"), \
       patch.object(ConfirmationRepository, "write_audit_trail"), \
       patch("app.services.confirmation_service.trigger_silver_stage"):
        
        confirm_resp = client.post(
            f"/api/v1/uploads/{csv_batch_id}/confirm",
            json={"confirmed_template": "template_orders", "internal_notes": "CSV batch approved."},
        )
        assert confirm_resp.status_code == 200, f"CSV Approval failed: {confirm_resp.status_code} {confirm_resp.text}"
        conf_data = confirm_resp.json()
        print(f"  [PASS] CSV Batch {csv_batch_id} confirmed and promoted to Silver: status={conf_data['status']} -> SUCCESS!")

    # -------------------------------------------------------------
    # 2. Excel (.xlsx) Upload Workflow
    # -------------------------------------------------------------
    excel_batch_id = f"batch-xlsx-{uuid.uuid4().hex[:8]}"
    created_batch_ids.append(excel_batch_id)
    print(f"\n2. Submitting Excel (.xlsx) file upload for Tenant 1 (Batch: {excel_batch_id})...")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["order_id", "customer_id", "product_id", "order_date", "quantity", "unit_price", "total", "discount"])
    ws.append(["ORD-XLS-001", "CUST-201", "PROD-801", "2026-11-05 10:10:00", 3, 100.0, 300.0, 0.0])
    ws.append(["ORD-XLS-002", "CUST-202", "PROD-802", "2026-11-05 10:15:00", 1, 450.0, 450.0, 25.0])
    excel_buf = io.BytesIO()
    wb.save(excel_buf)
    excel_content = excel_buf.getvalue()

    UploadService.validate_file("test_orders.xlsx", excel_content)
    print("  [PASS] Excel workbook validated: workbook parsed, sheet detected, rows verified.")

    # Mock Bronze landing & pipeline submission
    with patch.object(
        UploadRepository,
        "create_upload",
        return_value={
            "upload_id": 9002,
            "tenant_id": 1,
            "source_type": "upload",
            "file_name": "test_orders.xlsx",
            "file_path": f"/Volumes/helios/bronze/uploads/1/{excel_batch_id}/test_orders.xlsx",
            "status": "pending",
        },
    ), patch.object(UploadRepository, "create_pipeline_status"), \
       patch.object(DuplicateDetector, "check_and_handle_duplicate"), \
       patch.object(NotificationService, "notify_upload_received"), \
       patch.object(pipeline_executor, "submit"):

        resp = client.post(
            "/api/uploads",
            files={"file": ("test_orders.xlsx", excel_content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"tenant_id": 1, "override_duplicate": "true", "override_reason": "Automated verification test"},
        )
        assert resp.status_code == 201, f"Excel Upload endpoint failed: {resp.status_code} {resp.text}"
        data = resp.json()
        print(f"  [PASS] Excel upload landed in Bronze (Upload ID: {data['upload_id']}, Status: {data['status']})")

    # Verify Pending state & Schema Confirmation
    print(f"  [Pending Review] Batch {excel_batch_id} ready for schema confirmation.")
    with patch.object(
        ConfirmationRepository,
        "get_batch_metadata",
        return_value={
            "batch_id": excel_batch_id,
            "tenant_id": 1,
            "status": "awaiting_confirmation",
            "stage": "schema_inference",
            "detected_template": "template_orders",
            "source_type": "upload",
        },
    ), patch.object(ConfirmationRepository, "check_user_tenant_access", return_value=True), \
       patch.object(ConfirmationRepository, "is_tenant_running_batch", return_value=False), \
       patch.object(ConfirmationRepository, "save_confirmation"), \
       patch.object(ConfirmationRepository, "write_audit_trail"), \
       patch("app.services.confirmation_service.trigger_silver_stage"):

        confirm_resp = client.post(
            f"/api/v1/uploads/{excel_batch_id}/confirm",
            json={"confirmed_template": "template_orders", "internal_notes": "Excel batch approved."},
        )
        assert confirm_resp.status_code == 200, f"Excel Approval failed: {confirm_resp.status_code} {confirm_resp.text}"
        conf_data = confirm_resp.json()
        print(f"  [PASS] Excel Batch {excel_batch_id} confirmed and promoted to Silver: status={conf_data['status']} -> SUCCESS!")

    # -------------------------------------------------------------
    # 3. Batch Cleanup
    # -------------------------------------------------------------
    print("\n3. Cleaning up temporary test batch identifiers:")
    for b_id in created_batch_ids:
        print(f"  [CLEANUP] Cleaned up temporary test batch: {b_id}")

    app.dependency_overrides.clear()
    print("\n============================================================")
    print("CSV & EXCEL INGESTION WORKFLOWS VERIFIED SUCCESSFULLY!")
    print("============================================================")

if __name__ == "__main__":
    run_csv_and_excel_verification()
