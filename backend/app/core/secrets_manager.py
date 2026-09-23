import base64
import logging
import uuid
from typing import Optional, Union

from cryptography.fernet import Fernet
from databricks.sdk import WorkspaceClient

from app.core.config import settings

logger = logging.getLogger("helios.secrets_manager")


def get_databricks_workspace_client() -> WorkspaceClient:
    """Instantiate Databricks SDK WorkspaceClient using application settings."""
    return WorkspaceClient(
        host=settings.DATABRICKS_SERVER_HOSTNAME,
        token=settings.DATABRICKS_TOKEN,
    )


def decode_secret_value(raw_val: str) -> str:
    """Decode Databricks Secrets base64 string or return plain string."""
    try:
        decoded_bytes = base64.b64decode(raw_val.encode("utf-8"), validate=True)
        return decoded_bytes.decode("utf-8")
    except Exception:
        return raw_val


def sanitize_error_message(exc: Union[Exception, str], secret: Optional[str] = None) -> str:
    """Scrub plaintext secrets or passwords from exception messages and log strings."""
    msg = str(exc)
    if secret and secret in msg:
        msg = msg.replace(secret, "******")
    return msg


def store_db_credential(
    tenant_id: int,
    connection_id: Optional[Union[int, str]],
    password: str,
    client: Optional[WorkspaceClient] = None,
) -> str:
    """
    Writes the password into Databricks Secrets (via the Databricks SDK) under a scoped
    secret key such as helios-tenant-{tenant_id}-conn-{connection_id}.
    
    Returns only the key reference to be stored in platform.db_connections (e.g. scope:key).
    """
    scope = f"helios_tenant_{tenant_id}"
    conn_suffix = str(connection_id) if connection_id is not None else uuid.uuid4().hex[:12]
    key = f"helios-tenant-{tenant_id}-conn-{conn_suffix}"

    ws = client or get_databricks_workspace_client()

    try:
        ws.secrets.create_scope(scope=scope)
    except Exception as exc:
        logger.debug("Secret scope '%s' already exists or creation skipped: %s", scope, exc)

    ws.secrets.put_secret(scope=scope, key=key, string_value=password)
    return f"{scope}:{key}"


def retrieve_db_credential(
    secret_key_ref: str,
    client: Optional[WorkspaceClient] = None,
) -> str:
    """
    Fetches the password from Databricks Secrets at the moment of use only
    (e.g., during sync_now()). Never caches it beyond the single operation.
    """
    if not secret_key_ref or not secret_key_ref.strip():
        raise ValueError("Secret key reference cannot be empty.")

    if ":" in secret_key_ref:
        scope, key = secret_key_ref.split(":", 1)
    else:
        scope = "helios"
        key = secret_key_ref

    ws = client or get_databricks_workspace_client()
    resp = ws.secrets.get_secret(scope=scope, key=key)

    if not resp or not resp.value:
        raise RuntimeError(f"Databricks secret '{secret_key_ref}' not found or empty.")

    return decode_secret_value(resp.value)


def get_fernet_cipher() -> Fernet:
    """Initialize Fernet symmetric cipher using CREDENTIAL_ENCRYPTION_KEY from environment."""
    key = settings.CREDENTIAL_ENCRYPTION_KEY
    if not key:
        raise ValueError("CREDENTIAL_ENCRYPTION_KEY is not configured in environment.")
    return Fernet(key.encode("utf-8"))


def encrypt_field(value: str) -> str:
    """
    Secondary encryption layer using the `cryptography` library's Fernet symmetric encryption,
    keyed by CREDENTIAL_ENCRYPTION_KEY from environment config, for any additional sensitive
    metadata that isn't a full credential but still warrants protection.
    """
    if value is None:
        raise ValueError("Cannot encrypt None value.")
    cipher = get_fernet_cipher()
    return cipher.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_field(value: str) -> str:
    """
    Decrypts a Fernet-encrypted ciphertext string back to plaintext using CREDENTIAL_ENCRYPTION_KEY.
    """
    if value is None:
        raise ValueError("Cannot decrypt None value.")
    cipher = get_fernet_cipher()
    return cipher.decrypt(value.encode("utf-8")).decode("utf-8")
