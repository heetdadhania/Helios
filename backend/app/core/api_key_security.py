import hashlib
import hmac
import secrets

API_KEY_PREFIX = "helios_live_"


def generate_api_key(prefix: str = API_KEY_PREFIX) -> str:
    """Generate a cryptographically random API key token with standard prefix."""
    random_suffix = secrets.token_urlsafe(32)
    return f"{prefix}{random_suffix}"


def hash_api_key(key: str) -> str:
    """Compute one-way SHA-256 cryptographic hash of raw API key for secure persistence."""
    cleaned = key.strip()
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()


def verify_api_key(key: str, stored_hash: str) -> bool:
    """Perform constant-time cryptographic verification of raw API key against stored hash."""
    computed_hash = hash_api_key(key)
    return hmac.compare_digest(computed_hash, stored_hash)


def mask_api_key(key: str, prefix: str = API_KEY_PREFIX) -> str:
    """Create a masked string displaying only the prefix and the final 4 characters."""
    cleaned = key.strip()
    if len(cleaned) <= 12:
        return f"{prefix}••••"
    suffix = cleaned[-4:]
    return f"{prefix}••••{suffix}"
