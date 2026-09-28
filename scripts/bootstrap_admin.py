"""
Helios Platform - One-time Initial Admin Bootstrap Script

Provisions the initial Administrator account in the platform.users Delta table.
Idempotent: If any user with role='admin' already exists, exits safely without modifications.

Usage:
    python scripts/bootstrap_admin.py
"""

import os
import sys
from pathlib import Path

# Add backend directory to sys.path so app modules can be resolved
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR if (CURRENT_DIR / "app").is_dir() else (
    CURRENT_DIR.parent if (CURRENT_DIR.parent / "app").is_dir() else CURRENT_DIR.parent / "backend"
)

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Load environment variables
from dotenv import load_dotenv

for env_candidate in [
    BACKEND_DIR / ".env",
    Path.cwd() / ".env",
    CURRENT_DIR.parent / ".env",
]:
    if env_candidate.is_file():
        load_dotenv(dotenv_path=env_candidate, override=False)
        break

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.base import databricks_cursor


def bootstrap_admin() -> int:
    """
    Check for existing admin users in platform.users and create the initial admin if none exist.
    Returns 0 on success or existing admin, 1 on configuration error.
    """
    admin_email = os.getenv("BOOTSTRAP_ADMIN_EMAIL")
    admin_password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD")
    admin_name = os.getenv("BOOTSTRAP_ADMIN_NAME", "Helios Administrator")

    if not admin_email or not admin_password:
        print("[ERROR] Missing required environment variables:")
        if not admin_email:
            print("  - BOOTSTRAP_ADMIN_EMAIL is not set.")
        if not admin_password:
            print("  - BOOTSTRAP_ADMIN_PASSWORD is not set.")
        print("Please configure them in your environment or .env file.")
        return 1

    clean_email = admin_email.strip().lower()
    table_name = f"`{settings.DATABRICKS_CATALOG}`.`platform`.`users`"

    print(f"[INFO] Connecting to Databricks and checking {table_name} for existing admin users...")

    with databricks_cursor() as cursor:
        # Check whether ANY row with role='admin' already exists
        check_query = f"SELECT count(*) FROM {table_name} WHERE lower(role) = 'admin'"
        cursor.execute(check_query)
        result = cursor.fetchone()
        admin_count = result[0] if result else 0

        if admin_count > 0:
            print(
                f"[INFO] An administrator already exists in {table_name} "
                f"({admin_count} admin user(s) found). No changes made."
            )
            return 0

        # Check if email is already taken by a different role
        cursor.execute(
            f"SELECT count(*) FROM {table_name} WHERE lower(email) = :email",
            {"email": clean_email},
        )
        email_result = cursor.fetchone()
        email_count = email_result[0] if email_result else 0
        if email_count > 0:
            print(
                f"[ERROR] A user with email '{clean_email}' already exists with a different role. "
                "Cannot bootstrap admin with this email."
            )
            return 1

        print("[INFO] No existing admin found. Generating password hash and creating account...")
        password_hash = get_password_hash(admin_password)

        insert_query = f"""
            INSERT INTO {table_name} (tenant_id, name, email, password_hash, role, is_active, created_at)
            VALUES (NULL, :name, :email, :password_hash, 'admin', true, current_timestamp())
        """
        cursor.execute(
            insert_query,
            {
                "name": admin_name.strip(),
                "email": clean_email,
                "password_hash": password_hash,
            },
        )

        print(f"[SUCCESS] Initial Admin user successfully created with email: {clean_email}")
        return 0


if __name__ == "__main__":
    sys.exit(bootstrap_admin())
