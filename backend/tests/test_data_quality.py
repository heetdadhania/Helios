import csv
import io
import json
import sys
from pathlib import Path
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
REPO_ROOT = BACKEND_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi import status
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user, get_db_cursor
from app.main import app
from app.repositories.data_quality_repository import DataQualityRepository
from app.schemas.auth import UserOut, UserRole


class TestDataQualityRepository(unittest.TestCase):
    """Test DataQualityRepository methods with mocked Databricks cursor."""

    def setUp(self):
        self.mock_cursor = MagicMock()
        self.repo = DataQualityRepository(self.mock_cursor, catalog="helios_catalog")

    def test_get_rejected_rows_csv_not_found(self):
        """Non-existent batch raises 404."""
        self.mock_cursor.fetchone.return_value = None
        with self.assertRaises(Exception) as ctx:
            self.repo.get_rejected_rows_csv("batch-missing", user_id=1, user_role="admin")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_get_rejected_rows_csv_unassigned_team_member(self):
        """Unassigned team member raises 403."""
        # 1. Batch found for tenant 5
        # 2. Team assignment check returns None (not assigned)
        self.mock_cursor.fetchone.side_effect = [
            (5,),   # pipeline_status lookup
            None,   # team_assignments lookup
        ]
        with self.assertRaises(Exception) as ctx:
            self.repo.get_rejected_rows_csv("batch-unassigned", user_id=2, user_role="team_member")
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("not assigned", ctx.exception.detail.lower())

    def test_get_rejected_rows_csv_admin_success(self):
        """Admin can download rejected rows CSV with BOM, original fields, and rejection reason."""
        self.mock_cursor.fetchone.side_effect = [
            (1,),  # batch lookup in pipeline_status -> tenant_id 1
        ]
        # dq rows: 2 rejected rows
        now = datetime.now(timezone.utc)
        dq_rows = [
            (101, "b-1", 1, "silver.orders_clean", "ORD-101", "missing_required_key: customer_id", now),
            (102, "b-1", 1, "silver.orders_clean", "ORD-102", "invalid_quantity: quantity must be greater than zero (original_value: -2)", now),
        ]
        # Bronze rows
        bronze_rows = [
            (1, json.dumps({"order_id": "ORD-100", "customer_id": "C-1", "quantity": 1, "total": 100.0})),
            (2, json.dumps({"order_id": "ORD-101", "customer_id": "", "quantity": 2, "total": 200.0})),
            (3, json.dumps({"order_id": "ORD-102", "customer_id": "C-2", "quantity": -2, "total": -200.0})),
        ]

        self.mock_cursor.fetchall.side_effect = [
            dq_rows,      # dq_table fetch
            bronze_rows,  # bronze_orders_table fetch
        ]

        csv_text = self.repo.get_rejected_rows_csv("b-1", user_id=1, user_role="admin")

        # Must start with UTF-8 BOM
        self.assertTrue(csv_text.startswith("\ufeff"))
        csv_bytes = csv_text.encode("utf-8")
        self.assertTrue(csv_bytes.startswith(b"\xef\xbb\xbf"))

        # Parse CSV without BOM
        reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))
        rows = list(reader)

        # Row count equals quality-log count (2 == 2)
        self.assertEqual(len(rows), 2)

        # Check fields
        self.assertIn("order_id", rows[0])
        self.assertIn("rejection_reason", rows[0])
        self.assertEqual(rows[0]["order_id"], "ORD-101")
        self.assertIn("customer_id", rows[0]["rejection_reason"])

        self.assertEqual(rows[1]["order_id"], "ORD-102")
        self.assertIn("quantity", rows[1]["rejection_reason"])

    def test_get_rejected_rows_csv_team_member_assigned_success(self):
        """Assigned team member query enforces team_assignments join and succeeds."""
        self.mock_cursor.fetchone.side_effect = [
            (1,),   # pipeline_status lookup -> tenant_id 1
            (1,),   # team_assignments lookup -> assigned!
        ]
        now = datetime.now(timezone.utc)
        dq_rows = [
            (201, "b-assigned", 1, "silver.orders_clean", "ORD-201", "invalid_date_fields: order_date", now),
        ]
        bronze_rows = [
            (1, json.dumps({"order_id": "ORD-201", "order_date": "not-a-date", "total": 500.0})),
        ]
        self.mock_cursor.fetchall.side_effect = [
            dq_rows,
            bronze_rows,
        ]

        csv_text = self.repo.get_rejected_rows_csv("b-assigned", user_id=10, user_role="team_member")
        self.assertTrue(csv_text.startswith("\ufeff"))
        reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))
        rows = list(reader)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["order_id"], "ORD-201")
        self.assertIn("not-a-date", rows[0]["order_date"])
        self.assertIn("invalid_date_fields", rows[0]["rejection_reason"])


class TestDataQualityAPI(unittest.TestCase):
    """Integration tests for GET /api/v1/quality/rejected-rows/{batch_id}.csv endpoint."""

    def setUp(self):
        self.client = TestClient(app)
        self.mock_cursor = MagicMock()
        app.dependency_overrides[get_db_cursor] = lambda: self.mock_cursor

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_admin_download_rejected_rows_csv(self):
        admin_user = UserOut(
            id=1,
            name="Admin User",
            email="admin@helios.io",
            role=UserRole.ADMIN,
            tenant_id=None,
        )
        app.dependency_overrides[get_current_user] = lambda: admin_user

        with patch("app.repositories.data_quality_repository.DataQualityRepository.get_rejected_rows_csv") as mock_csv:
            mock_csv.return_value = "\ufefforder_id,total,rejection_reason\r\nORD-1,100,missing_order_id\r\n"
            resp = self.client.get("/api/v1/quality/rejected-rows/batch-999.csv")
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
            self.assertEqual(resp.headers["content-type"], "text/csv; charset=utf-8")
            self.assertIn('filename="rejected_rows_batch-999.csv"', resp.headers["content-disposition"])
            self.assertTrue(resp.content.startswith(b"\xef\xbb\xbf"))

    def test_team_member_unassigned_rejected_rows_returns_403(self):
        team_user = UserOut(
            id=2,
            name="Team Member",
            email="team@helios.io",
            role=UserRole.TEAM_MEMBER,
            tenant_id=None,
        )
        app.dependency_overrides[get_current_user] = lambda: team_user

        # Mock repository raising 403
        with patch("app.repositories.data_quality_repository.DataQualityRepository.get_rejected_rows_csv") as mock_csv:
            from fastapi import HTTPException
            mock_csv.side_effect = HTTPException(status_code=403, detail="Access denied: You are not assigned to organization 5.")
            resp = self.client.get("/api/v1/quality/rejected-rows/batch-org5.csv")
            self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
            self.assertIn("not assigned", resp.json()["detail"].lower())

    def test_smb_owner_forbidden(self):
        smb_user = UserOut(
            id=3,
            name="SMB Owner",
            email="owner@example.com",
            role=UserRole.SMB_OWNER,
            tenant_id=1,
        )
        app.dependency_overrides[get_current_user] = lambda: smb_user

        resp = self.client.get("/api/v1/quality/rejected-rows/batch-1.csv")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


if __name__ == "__main__":
    unittest.main()
