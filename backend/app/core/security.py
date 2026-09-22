from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
import jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from app.core.config import settings

# Passlib CryptContext using standard bcrypt hashing scheme
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify that a plaintext password matches the bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate a secure bcrypt hash from a plaintext password string."""
    return pwd_context.hash(password)


def create_access_token(
    user_id: Union[int, str],
    role: str,
    tenant_id: Optional[int] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Encode and sign a JWT access token.
    
    Payload includes:
      - sub: user_id (stringified)
      - role: smb_owner | team_member | admin
      - tenant_id: organization ID or None
      - exp: token expiry epoch timestamp
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "tenant_id": tenant_id,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a signed JWT access token, returning the payload claims."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def get_fernet_cipher() -> Fernet:
    """Initialize Fernet symmetric cipher using CREDENTIAL_ENCRYPTION_KEY."""
    return Fernet(settings.CREDENTIAL_ENCRYPTION_KEY.encode())


def encrypt_credential(plain_text: str) -> str:
    """Encrypt a plaintext secret (connector tokens, secret references) using Fernet."""
    cipher = get_fernet_cipher()
    return cipher.encrypt(plain_text.encode("utf-8")).decode("utf-8")


def decrypt_credential(cipher_text: str) -> str:
    """Decrypt a Fernet-encrypted secret string."""
    cipher = get_fernet_cipher()
    return cipher.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
