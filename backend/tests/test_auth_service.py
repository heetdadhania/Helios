import unittest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.core import security
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService


class TestAuthServiceAndRepository(unittest.TestCase):
    """Test suite for authentication, retry-with-backoff, and distinct outcome error handling."""

    def setUp(self):
        self.password_plain = "ValidSecret123!"
        self.password_hash = security.get_password_hash(self.password_plain)
        self.valid_user = {
            "user_id": 42,
            "name": "Test User",
            "email": "test@helios.io",
            "password_hash": self.password_hash,
            "role": "admin",
            "tenant_id": None,
            "is_active": True,
        }

    def test_database_connection_error_raises_503_never_401(self):
        """Database connection/query error must raise HTTP 503, never 401."""
        mock_cursor = MagicMock()
        with patch.object(
            UserRepository,
            "get_by_email",
            side_effect=RuntimeError("Databricks Warehouse is waking up"),
        ):
            with self.assertRaises(HTTPException) as ctx:
                AuthService.authenticate_user(
                    cursor=mock_cursor,
                    email="test@helios.io",
                    password=self.password_plain,
                )
            self.assertEqual(ctx.exception.status_code, 503)
            self.assertIn("temporarily unavailable", ctx.exception.detail.lower())

    def test_user_not_found_raises_401(self):
        """Non-existent user must raise HTTP 401 with standard message."""
        mock_cursor = MagicMock()
        with patch.object(UserRepository, "get_by_email", return_value=None):
            with self.assertRaises(HTTPException) as ctx:
                AuthService.authenticate_user(
                    cursor=mock_cursor,
                    email="nonexistent@helios.io",
                    password=self.password_plain,
                )
            self.assertEqual(ctx.exception.status_code, 401)
            self.assertEqual(ctx.exception.detail, "Invalid email or password.")

    def test_password_mismatch_raises_401_and_never_retried(self):
        """Incorrect password must raise HTTP 401 and must NOT retry password verification."""
        mock_cursor = MagicMock()
        with patch.object(UserRepository, "get_by_email", return_value=self.valid_user):
            with patch.object(AuthService, "verify_password", wraps=AuthService.verify_password) as mock_verify:
                with self.assertRaises(HTTPException) as ctx:
                    AuthService.authenticate_user(
                        cursor=mock_cursor,
                        email="test@helios.io",
                        password="WrongPassword123!",
                    )
                self.assertEqual(ctx.exception.status_code, 401)
                self.assertEqual(ctx.exception.detail, "Invalid email or password.")
                # Confirm password verification was invoked exactly once
                self.assertEqual(mock_verify.call_count, 1)

    def test_deactivated_user_raises_401(self):
        """Deactivated user account must raise HTTP 401 with deactivated message."""
        mock_cursor = MagicMock()
        deactivated_user = dict(self.valid_user)
        deactivated_user["is_active"] = False

        with patch.object(UserRepository, "get_by_email", return_value=deactivated_user):
            with self.assertRaises(HTTPException) as ctx:
                AuthService.authenticate_user(
                    cursor=mock_cursor,
                    email="test@helios.io",
                    password=self.password_plain,
                )
            self.assertEqual(ctx.exception.status_code, 401)
            self.assertIn("deactivated", ctx.exception.detail.lower())

    def test_successful_authentication(self):
        """Valid credentials return the user record."""
        mock_cursor = MagicMock()
        with patch.object(UserRepository, "get_by_email", return_value=self.valid_user):
            user = AuthService.authenticate_user(
                cursor=mock_cursor,
                email="test@helios.io",
                password=self.password_plain,
            )
            self.assertEqual(user["user_id"], 42)
            self.assertEqual(user["email"], "test@helios.io")

    def test_user_repository_retry_on_transient_failure_then_success(self):
        """UserRepository.get_by_email retries on transient error and succeeds."""
        mock_cursor = MagicMock()
        # Attempt 1 fails on mock_cursor
        mock_cursor.execute.side_effect = RuntimeError("Warehouse auto-suspended")

        repo = UserRepository(cursor=mock_cursor)

        # On retry, databricks_cursor provides a fresh working cursor
        fresh_cursor = MagicMock()
        fresh_cursor.description = [("user_id",), ("email",), ("password_hash",), ("is_active",)]
        fresh_cursor.fetchall.return_value = [(42, "test@helios.io", self.password_hash, True)]

        with patch("app.repositories.user_repository.databricks_cursor") as mock_db_ctx:
            mock_db_ctx.return_value.__enter__.return_value = fresh_cursor
            with patch("time.sleep") as mock_sleep:
                user = repo.get_by_email("test@helios.io", max_retries=3, base_backoff=0.01)
                self.assertIsNotNone(user)
                self.assertEqual(user["user_id"], 42)
                self.assertEqual(mock_sleep.call_count, 1)

    def test_user_repository_exhausts_retries_raises_exception(self):
        """UserRepository.get_by_email raises exception when all retries fail."""
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = RuntimeError("Continuous connection failure")

        repo = UserRepository(cursor=mock_cursor)

        fresh_cursor = MagicMock()
        fresh_cursor.execute.side_effect = RuntimeError("Warehouse wake-up timeout")

        with patch("app.repositories.user_repository.databricks_cursor") as mock_db_ctx:
            mock_db_ctx.return_value.__enter__.return_value = fresh_cursor
            with patch("time.sleep"):
                with self.assertRaises(RuntimeError):
                    repo.get_by_email("test@helios.io", max_retries=3, base_backoff=0.01)


if __name__ == "__main__":
    unittest.main()
