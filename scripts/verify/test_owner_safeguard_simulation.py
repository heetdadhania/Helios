#!/usr/bin/env python3
"""
Test script simulating a concurrent second owner insert to verify the
cheap safeguard in check_and_safeguard_single_owner:
- Inserts a simulated second active owner for a tenant
- Runs check_and_safeguard_single_owner
- Confirms HTTPException 409 is raised
- Confirms the second owner was immediately deactivated (is_active = false)
- Cleans up the simulated test user
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
load_dotenv(REPO_ROOT / ".env")

from fastapi import HTTPException
from app.db.base import databricks_cursor
from app.core.config import settings
from app.services.owner_service import check_and_safeguard_single_owner
from app.repositories.user_repository import UserRepository

def test_simulated_second_owner_insert():
    print("=" * 70)
    print("TEST: SIMULATED CONCURRENT SECOND OWNER INSERT SAFEGUARD")
    print("=" * 70)
    
    catalog = settings.DATABRICKS_CATALOG
    user_repo = UserRepository()
    test_email = "test_concurrent_owner_sim@helios-test.dev"
    tenant_id = 1
    
    with databricks_cursor() as cur:
        # Ensure clean state for test email
        cur.execute(f"DELETE FROM `{catalog}`.`platform`.`users` WHERE lower(email) = :email", {"email": test_email})
        
        # Insert simulated second active owner for Tenant 1 (which already has an owner)
        cur.execute(
            f"""
            INSERT INTO `{catalog}`.`platform`.`users` 
            (name, email, password_hash, role, tenant_id, is_active, must_change_password)
            VALUES (:name, :email, :hash, 'smb_owner', :tenant_id, true, false)
            """,
            {
                "name": "Simulated Duplicate Owner",
                "email": test_email,
                "hash": "simulated_dummy_hash",
                "tenant_id": tenant_id,
            }
        )
        
        # Retrieve user_id of the newly inserted simulated user
        cur.execute(f"SELECT user_id, is_active FROM `{catalog}`.`platform`.`users` WHERE email = :email", {"email": test_email})
        row = cur.fetchone()
        assert row is not None, "Failed to insert simulated test owner"
        sim_user_id = int(row[0])
        print(f"Simulated second owner created: user_id={sim_user_id}, is_active={row[1]}")
        
        caught_409 = False
        try:
            # Trigger the safeguard
            check_and_safeguard_single_owner(tenant_id=tenant_id, new_user_id=sim_user_id, cursor=cur)
        except HTTPException as exc:
            if exc.status_code == 409:
                caught_409 = True
                print(f"[PASS] Safeguard raised expected 409: {exc.detail}")
            else:
                raise
        
        assert caught_409, "Expected 409 HTTPException was not raised by safeguard!"
        
        # Verify in DB that the newer owner was deactivated
        cur.execute(f"SELECT is_active FROM `{catalog}`.`platform`.`users` WHERE user_id = :uid", {"uid": sim_user_id})
        check_row = cur.fetchone()
        assert check_row is not None, "User not found"
        is_active = bool(check_row[0])
        print(f"Status of simulated owner in database after safeguard: is_active={is_active}")
        assert not is_active, f"Expected is_active=False, got {is_active}"
        print("[PASS] Newer duplicate owner was successfully deactivated in DB.")
        
        # Clean up test row
        cur.execute(f"DELETE FROM `{catalog}`.`platform`.`users` WHERE user_id = :uid", {"uid": sim_user_id})
        print(f"Cleaned up simulated test user_id={sim_user_id}")
        
    print("\n" + "=" * 70)
    print("SIMULATION TEST PASSED: Safeguard prevented multiple active owners!")
    print("=" * 70)

if __name__ == "__main__":
    test_simulated_second_owner_insert()
