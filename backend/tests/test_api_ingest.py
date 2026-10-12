import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.api_key_auth import (
    ApiKeyContext,
    SlidingWindowRateLimiter,
    get_api_key_context,
    rate_limiter,
)
from app.core.dependencies import get_current_user, get_db_cursor
from app.main import app
from app.repositories.api_key_repository import ApiKeyRepository
from app.repositories.upload_repository import UploadRepository
from app.schemas.api_ingest import (
    ApiIngestPayload,
    ApiIngestResponse,
    ApiKeyGeneratedOut,
    ApiKeyOut,
)
from app.schemas.auth import UserOut, UserRole
from app.services.api_ingest_service import ApiIngestService
from app.services.api_key_service import ApiKeyService


class TestApiKeyService(unittest.TestCase):
    """Test cryptographic generation, hashing, and masking of API keys."""

    def test_generate_api_key(self):
        key = ApiKeyService.generate_api_key()
        self.assertTrue(key.startswith("helios_live_"))
        self.assertGreater(len(key), 40)

    def test_hash_and_verify_api_key(self):
        raw_key = ApiKeyService.generate_api_key()
        hashed = ApiKeyService.hash_api_key(raw_key)
        self.assertEqual(len(hashed), 64)  # SHA-256 hex length
        self.assertTrue(ApiKeyService.verify_api_key(raw_key, hashed))
        self.assertFalse(ApiKeyService.verify_api_key("wrong_key", hashed))

    def test_mask_api_key(self):
        raw_key = "helios_live_abcdef1234567890"
        masked = ApiKeyService.mask_api_key(raw_key)
        self.assertEqual(masked, "helios_live_••••7890")

    def test_regenerate_api_key(self):
        mock_repo = MagicMock(spec=ApiKeyRepository)
        mock_repo.create.return_value = {
            "api_key_id": 99,
            "tenant_id": 42,
            "key_hash": "dummyhash",
            "key_prefix": "helios_live_••••1234",
            "created_at": datetime.now(timezone.utc),
        }

        result = ApiKeyService.regenerate_api_key(tenant_id=42, repo=mock_repo)
        mock_repo.revoke_by_tenant.assert_called_once_with(42)
        mock_repo.create.assert_called_once()
        self.assertEqual(result.api_key_id, 99)
        self.assertEqual(result.tenant_id, 42)
        self.assertTrue(result.api_key.startswith("helios_live_"))
        self.assertTrue(result.masked_key.startswith("helios_live_••••"))


class TestApiKeyRepository(unittest.TestCase):
    """Test repository interactions for platform.api_keys table."""

    def setUp(self):
        self.cursor = MagicMock()
        self.repo = ApiKeyRepository(self.cursor, catalog="helios")

    def test_create(self):
        self.repo.execute_non_query = MagicMock()
        self.repo.execute_single = MagicMock(return_value={
            "api_key_id": 1,
            "tenant_id": 10,
            "key_hash": "sha256hash",
            "key_prefix": "helios_live_••••1111",
            "created_at": datetime.now(timezone.utc),
            "last_used_at": None,
            "is_active": True,
        })

        rec = self.repo.create(tenant_id=10, key_hash="sha256hash", key_prefix="helios_live_••••1111")
        self.repo.execute_non_query.assert_called_once()
        self.assertEqual(rec["api_key_id"], 1)

    def test_get_by_hash(self):
        self.repo.execute_single = MagicMock(return_value={"api_key_id": 1, "tenant_id": 10})
        rec = self.repo.get_by_hash("sha256hash")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["tenant_id"], 10)

    def test_revoke_by_tenant(self):
        self.repo.execute_non_query = MagicMock()
        self.repo.revoke_by_tenant(10)
        self.repo.execute_non_query.assert_called_once()


class TestRateLimiter(unittest.TestCase):
    """Test sliding window rate limiting logic."""

    def test_rate_limiter_permits_under_threshold(self):
        limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=10)
        for _ in range(5):
            self.assertTrue(limiter.is_allowed(1))
        # 6th request should be denied
        self.assertFalse(limiter.is_allowed(1))

    def test_rate_limiter_distinct_keys(self):
        limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=10)
        self.assertTrue(limiter.is_allowed(1))
        self.assertTrue(limiter.is_allowed(1))
        self.assertFalse(limiter.is_allowed(1))
        # Different key should still be permitted
        self.assertTrue(limiter.is_allowed(2))


class TestApiIngestService(unittest.TestCase):
    """Test ingestion shape validation and Bronze volume landing."""

    def test_validate_payload_shape_rejects_empty(self):
        with self.assertRaises(HTTPException) as ctx:
            ApiIngestService.validate_payload_shape([])
        self.assertEqual(ctx.exception.status_code, 400)

    def test_validate_payload_shape_rejects_invalid_record(self):
        with self.assertRaises(HTTPException) as ctx:
            ApiIngestService.validate_payload_shape([{}])  # type: ignore
        self.assertEqual(ctx.exception.status_code, 400)

    @patch("app.services.api_ingest_service.UploadService.save_file")
    def test_process_api_ingest_success(self, mock_save_file):
        mock_save_file.return_value = "/Volumes/helios/bronze/uploads/1/batch/file.csv"
        mock_upload_repo = MagicMock(spec=UploadRepository)
        mock_upload_repo.create_upload.return_value = {
            "upload_id": 55,
            "tenant_id": 1,
            "source_type": "api_push",
            "status": "pending",
        }

        records = [
            {"order_id": "ORD-1", "amount": 100.0, "status": "completed"},
            {"order_id": "ORD-2", "amount": 150.0, "status": "pending"},
        ]

        resp = ApiIngestService.process_api_ingest(
            records=records,
            tenant_id=1,
            upload_repo=mock_upload_repo,
        )

        self.assertEqual(resp.records_received, 2)
        self.assertEqual(resp.status, "ingesting")
        mock_upload_repo.create_upload.assert_called_once()
        # Verify tagged with source_type='api_push'
        self.assertEqual(
            mock_upload_repo.create_upload.call_args[1]["source_type"],
            "api_push",
        )
        mock_upload_repo.create_pipeline_status.assert_called_once()


class TestApiIngestEndpoints(unittest.TestCase):
    """Integration test suite for /api/ingest and /api/api-keys."""

    def setUp(self):
        self.client = TestClient(app)
        self.smb_user = UserOut(
            id=10,
            name="Alice Owner",
            email="alice@store.com",
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
        rate_limiter.reset()

    def tearDown(self):
        app.dependency_overrides.clear()
        rate_limiter.reset()

    def test_ingest_rejects_missing_api_key_header(self):
        res = self.client.post("/api/ingest", json={"records": [{"id": 1}]})
        self.assertEqual(res.status_code, 401)
        self.assertIn("API key missing", res.json()["detail"])

    def test_ingest_rejects_invalid_api_key(self):
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()
        with patch.object(ApiKeyRepository, "get_by_hash", return_value=None):
            res = self.client.post(
                "/api/ingest",
                headers={"X-Helios-Api-Key": "helios_live_invalid_key_123"},
                json={"records": [{"id": 1}]},
            )
            self.assertEqual(res.status_code, 401)
            self.assertIn("Invalid or revoked API key", res.json()["detail"])

    def test_ingest_success_with_valid_key(self):
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        with patch.object(
            ApiKeyRepository,
            "get_by_hash",
            return_value={"api_key_id": 1, "tenant_id": 42, "is_active": True},
        ), patch.object(
            ApiKeyRepository,
            "update_last_used",
        ), patch.object(
            ApiIngestService,
            "process_api_ingest",
            return_value=ApiIngestResponse(
                batch_id="batch-uuid-test",
                status="ingested",
                records_received=2,
            ),
        ):
            res = self.client.post(
                "/api/ingest",
                headers={"X-Helios-Api-Key": "helios_live_valid_key_123"},
                json={
                    "records": [
                        {"order_id": "ORD-1", "amount": 99.5},
                        {"order_id": "ORD-2", "amount": 149.0},
                    ]
                },
            )
            self.assertEqual(res.status_code, 201)
            data = res.json()
            self.assertEqual(data["batch_id"], "batch-uuid-test")
            self.assertEqual(data["records_received"], 2)
            self.assertEqual(data["status"], "ingested")

    def test_get_api_key_requires_smb_owner(self):
        app.dependency_overrides[get_current_user] = lambda: self.team_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        res = self.client.get("/api/api-keys")
        self.assertEqual(res.status_code, 403)

    def test_get_api_key_success(self):
        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        with patch.object(
            ApiKeyService,
            "get_tenant_api_key",
            return_value=ApiKeyOut(
                api_key_id=5,
                tenant_id=1,
                masked_key="helios_live_••••9999",
                created_at=datetime.now(timezone.utc),
                last_used_at=datetime.now(timezone.utc),
                is_active=True,
            ),
        ):
            res = self.client.get("/api/api-keys")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["masked_key"], "helios_live_••••9999")
            self.assertNotIn("key_hash", data)

    def test_regenerate_api_key_success(self):
        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        with patch.object(
            ApiKeyService,
            "regenerate_api_key",
            return_value=ApiKeyGeneratedOut(
                api_key_id=6,
                tenant_id=1,
                api_key="helios_live_new_secret_raw_key_123",
                masked_key="helios_live_••••_123",
                created_at=datetime.now(timezone.utc),
                message="Save this key now.",
            ),
        ):
            res = self.client.post("/api/api-keys/regenerate")
            self.assertEqual(res.status_code, 201)
            data = res.json()
            self.assertEqual(data["api_key"], "helios_live_new_secret_raw_key_123")
            self.assertIn("Save this key now", data["message"])


if __name__ == "__main__":
    unittest.main()
