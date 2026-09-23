import base64
import unittest
from unittest.mock import MagicMock

from app.core.api_key_security import (
    API_KEY_PREFIX,
    generate_api_key,
    hash_api_key,
    mask_api_key,
    verify_api_key,
)
from app.core.secrets_manager import (
    decode_secret_value,
    decrypt_field,
    encrypt_field,
    retrieve_db_credential,
    sanitize_error_message,
    store_db_credential,
)


class TestSecretsManager(unittest.TestCase):
    """Test suite for Databricks Secrets credential management and Fernet field encryption."""

    def test_store_db_credential_with_connection_id(self):
        mock_client = MagicMock()
        ref = store_db_credential(
            tenant_id=42,
            connection_id=101,
            password="SuperSecretPassword!99",
            client=mock_client,
        )

        # Verify scope and put_secret arguments
        mock_client.secrets.create_scope.assert_called_once_with(scope="helios_tenant_42")
        mock_client.secrets.put_secret.assert_called_once()
        kwargs = mock_client.secrets.put_secret.call_args[1]
        self.assertEqual(kwargs["scope"], "helios_tenant_42")
        self.assertEqual(kwargs["key"], "helios-tenant-42-conn-101")
        self.assertEqual(kwargs["string_value"], "SuperSecretPassword!99")
        self.assertEqual(ref, "helios_tenant_42:helios-tenant-42-conn-101")

    def test_store_db_credential_generates_unique_suffix_when_no_connection_id(self):
        mock_client = MagicMock()
        ref = store_db_credential(
            tenant_id=5,
            connection_id=None,
            password="TemporaryPassword123",
            client=mock_client,
        )

        self.assertTrue(ref.startswith("helios_tenant_5:helios-tenant-5-conn-"))
        kwargs = mock_client.secrets.put_secret.call_args[1]
        self.assertEqual(kwargs["scope"], "helios_tenant_5")
        self.assertIn("helios-tenant-5-conn-", kwargs["key"])

    def test_retrieve_db_credential_plain_string(self):
        mock_client = MagicMock()
        mock_secret_resp = MagicMock()
        mock_secret_resp.value = "PlainTextPassword456"
        mock_client.secrets.get_secret.return_value = mock_secret_resp

        password = retrieve_db_credential(
            secret_key_ref="helios_tenant_42:helios-tenant-42-conn-101",
            client=mock_client,
        )

        mock_client.secrets.get_secret.assert_called_once_with(
            scope="helios_tenant_42",
            key="helios-tenant-42-conn-101",
        )
        self.assertEqual(password, "PlainTextPassword456")

    def test_retrieve_db_credential_base64_encoded(self):
        mock_client = MagicMock()
        raw_password = "Base64SecretPassword!#"
        encoded_val = base64.b64encode(raw_password.encode("utf-8")).decode("utf-8")

        mock_secret_resp = MagicMock()
        mock_secret_resp.value = encoded_val
        mock_client.secrets.get_secret.return_value = mock_secret_resp

        password = retrieve_db_credential(
            secret_key_ref="helios_tenant_9:conn_key_abc",
            client=mock_client,
        )
        self.assertEqual(password, raw_password)

    def test_retrieve_db_credential_not_found_raises(self):
        mock_client = MagicMock()
        mock_client.secrets.get_secret.return_value = None

        with self.assertRaises(RuntimeError):
            retrieve_db_credential("helios_tenant_1:missing_key", client=mock_client)

    def test_retrieve_db_credential_empty_ref_raises(self):
        with self.assertRaises(ValueError):
            retrieve_db_credential("")

    def test_encrypt_and_decrypt_field(self):
        sensitive_metadata = '{"api_endpoint": "https://smb.corp/api", "api_token": "tok_xyz987"}'
        encrypted = encrypt_field(sensitive_metadata)

        # Ciphertext must differ completely from plaintext
        self.assertNotEqual(encrypted, sensitive_metadata)
        self.assertNotIn("tok_xyz987", encrypted)

        # Decryption restores original plaintext
        decrypted = decrypt_field(encrypted)
        self.assertEqual(decrypted, sensitive_metadata)

    def test_encrypt_field_none_raises(self):
        with self.assertRaises(ValueError):
            encrypt_field(None)  # type: ignore

    def test_decrypt_field_none_raises(self):
        with self.assertRaises(ValueError):
            decrypt_field(None)  # type: ignore

    def test_sanitize_error_message(self):
        raw_pass = "P@ssw0rd!Sensitive"
        msg = f"Failed to connect to host postgres.internal with password '{raw_pass}' on port 5432"
        sanitized = sanitize_error_message(Exception(msg), secret=raw_pass)

        self.assertNotIn(raw_pass, sanitized)
        self.assertIn("******", sanitized)

    def test_decode_secret_value_fallback(self):
        self.assertEqual(decode_secret_value("standard_unencoded_string"), "standard_unencoded_string")


class TestApiKeySecurity(unittest.TestCase):
    """Test suite for API key cryptographic generation, hashing, and verification."""

    def test_generate_api_key_format_and_uniqueness(self):
        key1 = generate_api_key()
        key2 = generate_api_key()

        self.assertTrue(key1.startswith(API_KEY_PREFIX))
        self.assertTrue(key2.startswith(API_KEY_PREFIX))
        self.assertNotEqual(key1, key2)
        # Token part should have sufficient entropy (urlsafe base64 of 32 bytes is ~43 chars)
        self.assertGreaterEqual(len(key1), len(API_KEY_PREFIX) + 32)

    def test_hash_api_key_one_way(self):
        raw_key = "helios_live_testkey_1234567890abcdef"
        hash1 = hash_api_key(raw_key)
        hash2 = hash_api_key(raw_key)

        # Deterministic SHA-256
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)
        # Raw key never appears in the hash
        self.assertNotIn(raw_key, hash1)

    def test_verify_api_key(self):
        raw_key = "helios_live_valid_key_ABCDEFGHIJKL"
        key_hash = hash_api_key(raw_key)

        self.assertTrue(verify_api_key(raw_key, key_hash))
        self.assertFalse(verify_api_key("helios_live_tampered_key", key_hash))

    def test_mask_api_key(self):
        raw_key = "helios_live_abcdef1234567890wxyz"
        masked = mask_api_key(raw_key)

        self.assertTrue(masked.startswith(API_KEY_PREFIX))
        self.assertTrue(masked.endswith("wxyz"))
        self.assertIn("••••", masked)
        # Middle characters are masked
        self.assertNotIn("1234567890", masked)
