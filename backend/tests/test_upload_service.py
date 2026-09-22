import io
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import openpyxl
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user, get_db_cursor
from app.main import app
from app.repositories.upload_repository import UploadRepository
from app.schemas.auth import UserOut, UserRole
from app.services.upload_service import UploadService


class TestUploadServiceValidation(unittest.TestCase):
    """Test validation rules for file format, size, emptiness, and headers."""

    def test_reject_unsupported_extensions(self):
        with self.assertRaises(HTTPException) as ctx:
            UploadService.validate_file("data.txt", b"some text")
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Unsupported file format", ctx.exception.detail)

        with self.assertRaises(HTTPException) as ctx:
            UploadService.validate_file("data.pdf", b"%PDF-1.4...")
        self.assertEqual(ctx.exception.status_code, 400)

    def test_reject_empty_file(self):
        with self.assertRaises(HTTPException) as ctx:
            UploadService.validate_file("orders.csv", b"")
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("File is empty", ctx.exception.detail)

    def test_reject_header_only_csv(self):
        header_only_csv = b"order_id,customer_id,total\n"
        with self.assertRaises(HTTPException) as ctx:
            UploadService.validate_file("orders.csv", header_only_csv)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("File contains only headers with no data rows", ctx.exception.detail)

    def test_reject_header_only_with_blank_lines_csv(self):
        header_only_csv = b"order_id,customer_id,total\n   \n,\n"
        with self.assertRaises(HTTPException) as ctx:
            UploadService.validate_file("orders.csv", header_only_csv)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("File contains only headers with no data rows", ctx.exception.detail)

    def test_accept_valid_csv(self):
        valid_csv = b"order_id,customer_id,total\nORD1001,CUST01,150.00\n"
        # Should not raise
        UploadService.validate_file("orders.csv", valid_csv)

    def test_reject_header_only_xlsx(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["order_id", "customer_id", "total"])
        buf = io.BytesIO()
        wb.save(buf)

        with self.assertRaises(HTTPException) as ctx:
            UploadService.validate_file("orders.xlsx", buf.getvalue())
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("File contains only headers with no data rows", ctx.exception.detail)

    def test_accept_valid_xlsx(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["order_id", "customer_id", "total"])
        ws.append(["ORD1001", "CUST01", 150.00])
        buf = io.BytesIO()
        wb.save(buf)

        # Should not raise
        UploadService.validate_file("orders.xlsx", buf.getvalue())

    def test_reject_oversized_file(self):
        oversized = b"a" * (10 * 1024 * 1024 + 1)
        with self.assertRaises(HTTPException) as ctx:
            UploadService.validate_file("orders.csv", oversized)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("exceeds the maximum permitted limit", ctx.exception.detail)


class TestUploadServiceStatusSimplification(unittest.TestCase):
    """Test plain-language customer-facing status mapping."""

    def test_failed_status_mapping(self):
        for raw in ["failed", "FAILED", "rejected", "error"]:
            stage, status_text = UploadService.simplify_status(raw)
            self.assertEqual(stage, "Failed")
            self.assertEqual(status_text, "Failed — please check your file and try again")

    def test_ready_status_mapping(self):
        for raw in ["success", "SUCCESS", "completed", "ready", "awaiting_confirmation"]:
            stage, status_text = UploadService.simplify_status(raw)
            self.assertEqual(stage, "Ready")
            self.assertEqual(status_text, "Ready")

    def test_processing_status_mapping(self):
        for raw in ["pending", "received", "ingested", "schema_inference_running", "silver_running", "gold_running"]:
            stage, status_text = UploadService.simplify_status(raw)
            self.assertEqual(stage, "Processing")
            self.assertEqual(status_text, "Processing")


class TestUploadAPIEndpoints(unittest.TestCase):
    """Integration test suite for /api/uploads endpoints using TestClient."""

    def setUp(self):
        self.client = TestClient(app)
        self.smb_user = UserOut(
            id=10,
            name="Alice Owner",
            email="alice@retailhub.com",
            role=UserRole.SMB_OWNER,
            tenant_id=1,
        )
        self.team_user = UserOut(
            id=20,
            name="Bob Team",
            email="bob@helios.io",
            role=UserRole.TEAM_MEMBER,
            tenant_id=None,
        )

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_upload_endpoint_requires_auth(self):
        response = self.client.post("/api/uploads", files={"file": ("test.csv", b"a,b\n1,2")})
        self.assertEqual(response.status_code, 401)

    def test_upload_endpoint_rejects_non_smb_owner(self):
        app.dependency_overrides[get_current_user] = lambda: self.team_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        response = self.client.post(
            "/api/uploads",
            files={"file": ("test.csv", b"a,b\n1,2", "text/csv")},
        )
        self.assertEqual(response.status_code, 403)

    def test_upload_endpoint_success(self):
        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        mock_cursor = MagicMock()
        app.dependency_overrides[get_db_cursor] = lambda: mock_cursor

        with patch.object(
            UploadRepository,
            "create_upload",
            return_value={
                "upload_id": 101,
                "tenant_id": 1,
                "source_type": "upload",
                "file_name": "sales.csv",
                "file_path": "/Volumes/helios/bronze/uploads/1/uuid/sales.csv",
                "status": "pending",
            },
        ), patch.object(UploadRepository, "create_pipeline_status") as mock_pipeline:
            csv_content = b"order_id,amount\nORD1,100\nORD2,200\n"
            response = self.client.post(
                "/api/uploads",
                files={"file": ("sales.csv", csv_content, "text/csv")},
            )
            self.assertEqual(response.status_code, 201)
            data = response.json()
            self.assertEqual(data["upload_id"], 101)
            self.assertEqual(data["status"], "pending")
            self.assertIn("batch_id", data)
            mock_pipeline.assert_called_once()

    def test_status_endpoint_simplified(self):
        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        mock_cursor = MagicMock()
        app.dependency_overrides[get_db_cursor] = lambda: mock_cursor

        with patch.object(
            UploadRepository,
            "get_by_id",
            return_value={"upload_id": 101, "tenant_id": 1, "status": "pending"},
        ), patch.object(
            UploadRepository,
            "get_pipeline_status_by_upload_id",
            return_value={
                "batch_id": "test-batch-uuid",
                "stage": "schema_inference",
                "status": "schema_inference_running",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        ):
            response = self.client.get("/api/uploads/101/status")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["batch_id"], "test-batch-uuid")
            self.assertEqual(data["stage"], "Processing")
            self.assertEqual(data["status"], "Processing")


if __name__ == "__main__":
    unittest.main()
