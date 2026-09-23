import io
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user, get_db_cursor
from app.main import app
from app.repositories.db_connection_repository import DbConnectionRepository
from app.repositories.upload_repository import UploadRepository
from app.schemas.auth import UserOut, UserRole
from app.schemas.db_connection import (
    DbConnectionCreate,
    DbConnectionOut,
    DbConnectionTestResult,
)
from app.services.db_connection_service import (
    DbConnectionService,
    decode_secret_value,
    sanitize_error_message,
)


class TestDbConnectionSchemas(unittest.TestCase):
    """Test validation and security attributes of DbConnection schemas."""

    def test_schema_valid_create(self):
        payload = DbConnectionCreate(
            db_type="postgresql",
            host="db.example.com",
            port=5432,
            database_name="app_db",
            username="svc_helios",
            password="SuperSecretPassword!",
            table_or_query="customers",
        )
        self.assertEqual(payload.db_type, "postgresql")
        self.assertEqual(payload.port, 5432)
        # Password should not appear in repr
        self.assertNotIn("SuperSecretPassword!", repr(payload))

    def test_schema_db_type_normalization(self):
        payload_pg = DbConnectionCreate(
            db_type="PGSQL",
            host="db.example.com",
            port=5432,
            database_name="app_db",
            username="user",
            password="pwd",
            table_or_query="users",
        )
        self.assertEqual(payload_pg.db_type, "postgresql")

        payload_ms = DbConnectionCreate(
            db_type="mssql",
            host="db.example.com",
            port=1433,
            database_name="app_db",
            username="user",
            password="pwd",
            table_or_query="orders",
        )
        self.assertEqual(payload_ms.db_type, "sqlserver")

    def test_out_schema_never_contains_password(self):
        out = DbConnectionOut(
            connection_id=1,
            tenant_id=10,
            db_type="mysql",
            host="127.0.0.1",
            port=3306,
            database_name="test_db",
            username="root",
            table_or_query="items",
            last_synced_at=None,
            created_at=datetime.now(timezone.utc),
            is_active=True,
        )
        data = out.model_dump()
        self.assertNotIn("password", data)
        self.assertNotIn("encrypted_credential_ref", data)
        self.assertEqual(data["connection_id"], 1)


class TestDbConnectionServiceHelpers(unittest.TestCase):
    """Test security masking and base64 helper functions."""

    def test_sanitize_error_message(self):
        secret = "P@ssw0rd123"
        exc = Exception(f"Failed to authenticate user 'admin' with password '{secret}' to host")
        sanitized = sanitize_error_message(exc, secret)
        self.assertNotIn(secret, sanitized)
        self.assertIn("******", sanitized)

    def test_decode_secret_value(self):
        import base64
        original = "SecretToken456!"
        encoded = base64.b64encode(original.encode("utf-8")).decode("utf-8")
        decoded = decode_secret_value(encoded)
        self.assertEqual(decoded, original)

        # Plain string fallback
        self.assertEqual(decode_secret_value("plain_val"), "plain_val")


class TestDbConnectionRepository(unittest.TestCase):
    """Test data access operations for platform.db_connections."""

    def setUp(self):
        self.cursor = MagicMock()
        self.repo = DbConnectionRepository(self.cursor, catalog="helios")

    def test_create(self):
        self.repo.execute_non_query = MagicMock()
        self.repo.execute_single = MagicMock(return_value={
            "connection_id": 5,
            "tenant_id": 1,
            "db_type": "mysql",
            "host": "localhost",
            "port": 3306,
            "database_name": "test_db",
            "username": "usr",
            "encrypted_credential_ref": "helios_tenant_1:key1",
            "table_or_query": "products",
            "is_active": True,
        })

        rec = self.repo.create(
            tenant_id=1,
            db_type="mysql",
            host="localhost",
            port=3306,
            database_name="test_db",
            username="usr",
            encrypted_credential_ref="helios_tenant_1:key1",
            table_or_query="products",
        )
        self.repo.execute_non_query.assert_called_once()
        self.assertEqual(rec["connection_id"], 5)

    def test_get_by_id_tenant_isolation(self):
        self.repo.execute_single = MagicMock(return_value={"connection_id": 5, "tenant_id": 1})
        res = self.repo.get_by_id(connection_id=5, tenant_id=1)
        self.assertIsNotNone(res)
        self.assertEqual(res["connection_id"], 5)
        # Verify query parameters passed to execute_single include tenant_id
        _, kwargs = self.repo.execute_single.call_args
        params = kwargs.get("parameters") or kwargs.get("params") or self.repo.execute_single.call_args[0][1]
        self.assertEqual(params["tenant_id"], 1)

    def test_list_by_tenant(self):
        self.repo.execute_query = MagicMock(return_value=[{"connection_id": 1}, {"connection_id": 2}])
        res = self.repo.list_by_tenant(tenant_id=1)
        self.assertEqual(len(res), 2)


class TestDbConnectionServiceOperations(unittest.TestCase):
    """Test connection testing, credential storage in Databricks Secrets, and sync logic."""

    @patch("app.services.db_connection_service.mysql.connector.connect")
    def test_test_connection_mysql_success(self, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        res = DbConnectionService.test_connection(
            db_type="mysql",
            host="127.0.0.1",
            port=3306,
            database_name="db",
            username="user",
            password="secret_password",
        )
        self.assertTrue(res.success)
        mock_connect.assert_called_once()
        # Verify TLS was enabled
        kwargs = mock_connect.call_args[1]
        self.assertFalse(kwargs.get("ssl_disabled", True))

    @patch("app.services.db_connection_service.psycopg2.connect")
    def test_test_connection_postgres_failure_sanitized(self, mock_connect):
        secret_pwd = "P@sswordSensitive!"
        mock_connect.side_effect = Exception(f"FATAL: password authentication failed for user with {secret_pwd}")

        res = DbConnectionService.test_connection(
            db_type="postgresql",
            host="127.0.0.1",
            port=5432,
            database_name="db",
            username="user",
            password=secret_pwd,
        )
        self.assertFalse(res.success)
        self.assertNotIn(secret_pwd, res.message)
        self.assertIn("******", res.message)

    def test_save_connection(self):
        mock_repo = MagicMock(spec=DbConnectionRepository)
        mock_repo.create.return_value = {
            "connection_id": 42,
            "tenant_id": 7,
            "db_type": "sqlserver",
            "host": "sql.corp.local",
            "port": 1433,
            "database_name": "inventory",
            "username": "svc_helios",
            "table_or_query": "SELECT * FROM stock",
            "last_synced_at": None,
            "created_at": datetime.now(timezone.utc),
            "is_active": True,
        }

        mock_secrets_client = MagicMock()
        conn_in = DbConnectionCreate(
            db_type="sqlserver",
            host="sql.corp.local",
            port=1433,
            database_name="inventory",
            username="svc_helios",
            password="raw_super_secret_password",
            table_or_query="SELECT * FROM stock",
        )

        out = DbConnectionService.save_connection(
            conn_in=conn_in,
            tenant_id=7,
            repo=mock_repo,
            secrets_client=mock_secrets_client,
        )

        self.assertEqual(out.connection_id, 42)
        self.assertEqual(out.db_type, "sqlserver")
        # Ensure Databricks secrets API put_secret was invoked with tenant scope
        mock_secrets_client.secrets.put_secret.assert_called_once()
        scope_arg = mock_secrets_client.secrets.put_secret.call_args[1]["scope"]
        self.assertEqual(scope_arg, "helios_tenant_7")

    @patch("app.services.db_connection_service.DbConnectionService.open_external_connection")
    @patch("app.services.db_connection_service.UploadService.save_file")
    def test_sync_now(self, mock_save_file, mock_open_conn):
        mock_repo = MagicMock(spec=DbConnectionRepository)
        mock_upload_repo = MagicMock(spec=UploadRepository)
        mock_secrets_client = MagicMock()

        mock_repo.get_by_id.return_value = {
            "connection_id": 42,
            "tenant_id": 7,
            "db_type": "mysql",
            "host": "mysql.host",
            "port": 3306,
            "database_name": "sales",
            "username": "usr",
            "encrypted_credential_ref": "helios_tenant_7:conn_secret_key",
            "table_or_query": "orders",
        }

        import base64
        mock_secret_resp = MagicMock()
        mock_secret_resp.value = base64.b64encode(b"retrieved_secret").decode()
        mock_secrets_client.secrets.get_secret.return_value = mock_secret_resp

        # Mock external database execution
        mock_ext_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.description = [("order_id",), ("amount",)]
        mock_cursor.fetchall.return_value = [("ORD100", 250.0), ("ORD101", 300.0)]
        mock_ext_conn.cursor.return_value = mock_cursor

        @patch.object(DbConnectionService, "open_external_connection")
        def run_test():
            pass

        mock_open_conn.return_value.__enter__.return_value = mock_ext_conn
        mock_save_file.return_value = "/Volumes/helios/bronze/uploads/7/batch-uuid/file.csv"

        mock_upload_repo.create_upload.return_value = {
            "upload_id": 99,
            "tenant_id": 7,
            "source_type": "db_connection",
            "status": "pending",
        }

        resp = DbConnectionService.sync_now(
            connection_id=42,
            tenant_id=7,
            user_id=1,
            repo=mock_repo,
            upload_repo=mock_upload_repo,
            secrets_client=mock_secrets_client,
        )

        self.assertEqual(resp.upload_id, 99)
        mock_upload_repo.create_upload.assert_called_once()
        # Verify tagged with source_type='db_connection'
        self.assertEqual(
            mock_upload_repo.create_upload.call_args[1]["source_type"],
            "db_connection",
        )
        mock_repo.update_last_synced.assert_called_once_with(connection_id=42, tenant_id=7)


class TestDbConnectionAPIEndpoints(unittest.TestCase):
    """Integration test suite for /api/db-connections endpoints using TestClient."""

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

    def test_endpoints_require_auth(self):
        res = self.client.post("/api/db-connections/test", json={
            "db_type": "mysql",
            "host": "localhost",
            "port": 3306,
            "database_name": "db",
            "username": "user",
            "password": "pwd",
            "table_or_query": "table",
        })
        self.assertEqual(res.status_code, 401)

    def test_endpoints_require_smb_owner(self):
        app.dependency_overrides[get_current_user] = lambda: self.team_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        res = self.client.post("/api/db-connections/test", json={
            "db_type": "mysql",
            "host": "localhost",
            "port": 3306,
            "database_name": "db",
            "username": "user",
            "password": "pwd",
            "table_or_query": "table",
        })
        self.assertEqual(res.status_code, 403)

    @patch.object(DbConnectionService, "test_connection")
    def test_post_test_connection_endpoint(self, mock_test):
        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        mock_test.return_value = DbConnectionTestResult(
            success=True,
            message="Connection verified successfully.",
        )

        res = self.client.post("/api/db-connections/test", json={
            "db_type": "postgresql",
            "host": "pg.example.com",
            "port": 5432,
            "database_name": "analytics",
            "username": "reader",
            "password": "supersecretpassword",
            "table_or_query": "orders",
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertNotIn("supersecretpassword", res.text)

    @patch.object(DbConnectionService, "save_connection")
    def test_post_create_connection_endpoint(self, mock_save):
        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        mock_save.return_value = DbConnectionOut(
            connection_id=10,
            tenant_id=1,
            db_type="postgresql",
            host="pg.example.com",
            port=5432,
            database_name="analytics",
            username="reader",
            table_or_query="orders",
            last_synced_at=None,
            created_at=datetime.now(timezone.utc),
            is_active=True,
        )

        res = self.client.post("/api/db-connections", json={
            "db_type": "postgresql",
            "host": "pg.example.com",
            "port": 5432,
            "database_name": "analytics",
            "username": "reader",
            "password": "supersecretpassword",
            "table_or_query": "orders",
        })
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["connection_id"], 10)
        self.assertNotIn("supersecretpassword", res.text)
        self.assertNotIn("password", data)

    @patch.object(DbConnectionRepository, "list_by_tenant")
    def test_get_connections_list(self, mock_list):
        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        mock_list.return_value = [
            {
                "connection_id": 1,
                "tenant_id": 1,
                "db_type": "mysql",
                "host": "mysql.acme.com",
                "port": 3306,
                "database_name": "store",
                "username": "helios",
                "table_or_query": "inventory",
                "last_synced_at": datetime.now(timezone.utc),
                "created_at": datetime.now(timezone.utc),
                "is_active": True,
            }
        ]

        res = self.client.get("/api/db-connections")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["host"], "mysql.acme.com")
        self.assertNotIn("password", data[0])

    @patch.object(DbConnectionService, "sync_now")
    def test_post_sync_endpoint(self, mock_sync):
        from app.schemas.upload import UploadResponse

        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        mock_sync.return_value = UploadResponse(
            upload_id=88,
            batch_id="batch-uuid-123",
            status="ingested",
        )

        res = self.client.post("/api/db-connections/1/sync")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["upload_id"], 88)
        self.assertEqual(data["status"], "ingested")
        self.assertEqual(data["batch_id"], "batch-uuid-123")


if __name__ == "__main__":
    unittest.main()
