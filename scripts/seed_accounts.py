#!/usr/bin/env python3
"""
Helios Data Platform - Seed Test Accounts & Tenants Script

Seeds 10 realistic tenants, 10 SMB Owner accounts, 5 Team Member accounts with
tenant assignments, and API keys for tenants 8-10. Safe to re-run (idempotent).

Usage:
    python scripts/seed_accounts.py
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Setup repository paths
CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent
BACKEND_DIR = REPO_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Load environment variables
from dotenv import load_dotenv

for env_path in [
    REPO_ROOT / ".env",
    BACKEND_DIR / ".env",
    Path.cwd() / ".env",
]:
    if env_path.is_file():
        load_dotenv(dotenv_path=env_path, override=False)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("helios.seed_accounts")

from app.core.api_key_security import generate_api_key, hash_api_key, mask_api_key
from app.core.config import settings
from app.core.security import get_password_hash
from app.db.base import databricks_cursor
from app.services.owner_service import ensure_no_active_owner


# -----------------------------------------------------------------------------
# Configuration: 10 Realistic Diverse Tenants & Ingestion Method Mappings
# -----------------------------------------------------------------------------
TENANT_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "index": 1,
        "business_name": "Kaveri Textiles & Crafts",
        "industry": "Apparel & Textiles",
        "contact_person_name": "Aarav Sharma",
        "contact_email": "contact@apexconsumer.com",
        "phone_number": "+91 98201 12345",
        "address_line1": "450 MG Road, Trinity Circle",
        "address_line2": "Suite 700",
        "city": "Bengaluru",
        "state": "Karnataka",
        "postal_code": "560001",
        "country": "India",
        "website_url": "https://www.kaveritextiles.in",
        "tax_id": "29ABCDE1234F1Z5",
        "ingestion_method": "File Upload (CSV/Excel)",
    },
    {
        "index": 2,
        "business_name": "Sahyadri Infotech Solutions",
        "industry": "Electronics & Hardware",
        "contact_person_name": "Rohan Kulkarni",
        "contact_email": "contact@pacifictech.jp",
        "phone_number": "+91 98210 23456",
        "address_line1": "18 Senapati Bapat Road",
        "address_line2": "Tower B, Level 14",
        "city": "Pune",
        "state": "Maharashtra",
        "postal_code": "411016",
        "country": "India",
        "website_url": "https://www.sahyadriinfotech.in",
        "tax_id": "27BCDEF2345G1Z6",
        "ingestion_method": "File Upload (CSV/Excel)",
    },
    {
        "index": 3,
        "business_name": "Nilgiri Home & Decor",
        "industry": "Home Goods & Living",
        "contact_person_name": "Ananya Iyer",
        "contact_email": "contact@vanguardhome.se",
        "phone_number": "+91 98401 34567",
        "address_line1": "56 Anna Salai, T. Nagar",
        "address_line2": None,
        "city": "Chennai",
        "state": "Tamil Nadu",
        "postal_code": "600017",
        "country": "India",
        "website_url": "https://www.nilgirihome.in",
        "tax_id": "33CDEFG3456H1Z7",
        "ingestion_method": "File Upload (CSV/Excel)",
    },
    {
        "index": 4,
        "business_name": "AyurVeda Botanicals",
        "industry": "Beauty & Personal Care",
        "contact_person_name": "Meera Nair",
        "contact_email": "care@velvetbotanicals.fr",
        "phone_number": "+91 98470 45678",
        "address_line1": "14 Marine Drive, Fort",
        "address_line2": "Building C",
        "city": "Kochi",
        "state": "Kerala",
        "postal_code": "682001",
        "country": "India",
        "website_url": "https://www.ayurvedabotanicals.in",
        "tax_id": "32DEFGH4567I1Z8",
        "ingestion_method": "File Upload (CSV/Excel)",
    },
    {
        "index": 5,
        "business_name": "Himalayan Peak Sports",
        "industry": "Sports & Fitness",
        "contact_person_name": "Vikram Chauhan",
        "contact_email": "contact@summitpeak.de",
        "phone_number": "+91 98160 56789",
        "address_line1": "35 The Mall Road, Civil Lines",
        "address_line2": None,
        "city": "Shimla",
        "state": "Himachal Pradesh",
        "postal_code": "171001",
        "country": "India",
        "website_url": "https://www.himalayansports.in",
        "tax_id": "02EFGHI5678J1Z9",
        "ingestion_method": "Database Connection (RDBMS - PostgreSQL)",
    },
    {
        "index": 6,
        "business_name": "Navneet Books & Media",
        "industry": "Books & Publishing",
        "contact_person_name": "Rajesh Patel",
        "contact_email": "editorial@pageandquill.co.uk",
        "phone_number": "+91 98250 67890",
        "address_line1": "22 Ashram Road, Navrangpura",
        "address_line2": "Suite 4B",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "postal_code": "380009",
        "country": "India",
        "website_url": "https://www.navneetbooks.in",
        "tax_id": "24FGHIJ6789K1Z0",
        "ingestion_method": "Database Connection (RDBMS - MySQL)",
    },
    {
        "index": 7,
        "business_name": "Channapatna Craftworks",
        "industry": "Toys & Handicrafts",
        "contact_person_name": "Suresh Gowda",
        "contact_email": "play@wonderkitetoys.ca",
        "phone_number": "+91 98801 78901",
        "address_line1": "350 Artisan Industrial Area",
        "address_line2": "Floor 2",
        "city": "Ramanagara",
        "state": "Karnataka",
        "postal_code": "562159",
        "country": "India",
        "website_url": "https://www.channapatnatoys.in",
        "tax_id": "29GHIJK7890L1Z1",
        "ingestion_method": "Database Connection (RDBMS - SQL Server)",
    },
    {
        "index": 8,
        "business_name": "Sundarbans Organic Grocers",
        "industry": "Grocery & Naturals",
        "contact_person_name": "Debashis Mukherjee",
        "contact_email": "orders@terraverde.it",
        "phone_number": "+91 98300 89012",
        "address_line1": "18 Park Street, Middleton Row",
        "address_line2": None,
        "city": "Kolkata",
        "state": "West Bengal",
        "postal_code": "700016",
        "country": "India",
        "website_url": "https://www.sundarbansorganics.in",
        "tax_id": "19HIJKL8901M1Z2",
        "ingestion_method": "REST API Push",
    },
    {
        "index": 9,
        "business_name": "Luminary Fine Gems",
        "industry": "Jewelry & Gems",
        "contact_person_name": "Priya Sharma",
        "contact_email": "concierge@luminarygems.in",
        "phone_number": "+91 98200 90123",
        "address_line1": "Bandra Kurla Complex, Tower B",
        "address_line2": "Floor 9",
        "city": "Mumbai",
        "state": "Maharashtra",
        "postal_code": "400051",
        "country": "India",
        "website_url": "https://www.luminarygems.in",
        "tax_id": "27AABCL1234F1Z5",
        "ingestion_method": "REST API Push",
    },
    {
        "index": 10,
        "business_name": "PashuCare Veterinary Supplies",
        "industry": "Pet Supplies & Care",
        "contact_person_name": "Arunabh Sengupta",
        "contact_email": "bark@pawsandtrails.com.au",
        "phone_number": "+91 98101 01234",
        "address_line1": "88 Connaught Place, Block C",
        "address_line2": "Unit 3",
        "city": "New Delhi",
        "state": "Delhi",
        "postal_code": "110001",
        "country": "India",
        "website_url": "https://www.pashucare.in",
        "tax_id": "07JKLMN0123O1Z4",
        "ingestion_method": "REST API Push",
    },
]

# -----------------------------------------------------------------------------
# Configuration: 5 Team Members
# -----------------------------------------------------------------------------
TEAM_MEMBER_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "index": 1,
        "name": "Sunita Deshmukh",
        "email": "team-member-1@helios-test.dev",
        "phone_number": "+91 98111 11001",
        "staff_id": "TM-101",
        "designation": "Senior Ingestion Analyst",
        "tenant_indices": [1, 2],
    },
    {
        "index": 2,
        "name": "Kavita Reddy",
        "email": "team-member-2@helios-test.dev",
        "phone_number": "+91 98222 11002",
        "staff_id": "TM-102",
        "designation": "Data Quality Operations Lead",
        "tenant_indices": [3, 4],
    },
    {
        "index": 3,
        "name": "Arjun Verma",
        "email": "team-member-3@helios-test.dev",
        "phone_number": "+91 98333 11003",
        "staff_id": "TM-103",
        "designation": "Pipeline Integration Specialist",
        "tenant_indices": [5, 6],
    },
    {
        "index": 4,
        "name": "Deepa Menon",
        "email": "team-member-4@helios-test.dev",
        "phone_number": "+91 98444 11004",
        "staff_id": "TM-104",
        "designation": "Customer Solutions Architect",
        "tenant_indices": [7, 8],
    },
    {
        "index": 5,
        "name": "Aditya Bhattacharya",
        "email": "team-member-5@helios-test.dev",
        "phone_number": "+91 98555 11005",
        "staff_id": "TM-105",
        "designation": "Enterprise Data Engineer",
        "tenant_indices": [9, 10],
    },
]


def seed_accounts() -> int:
    """Main execution function to provision all test tenants, users, and API keys."""
    # 1. Read test account password from environment
    password_plain = os.getenv("TEST_ACCOUNT_PASSWORD")
    if not password_plain or not password_plain.strip():
        logger.error(
            "TEST_ACCOUNT_PASSWORD environment variable is not set. "
            "Please configure it in .env or provide it in your shell environment."
        )
        return 1

    password_hash = get_password_hash(password_plain.strip())
    catalog = settings.DATABRICKS_CATALOG

    tenants_table = f"`{catalog}`.`platform`.`tenants`"
    users_table = f"`{catalog}`.`platform`.`users`"
    assignments_table = f"`{catalog}`.`platform`.`team_assignments`"
    api_keys_table = f"`{catalog}`.`platform`.`api_keys`"

    logger.info("Starting Helios test accounts seeding against catalog '%s'...", catalog)

    with databricks_cursor() as cursor:
        # ---------------------------------------------------------------------
        # STEP 1: Upsert 10 Tenants
        # ---------------------------------------------------------------------
        logger.info("Upserting 10 test tenant organizations...")
        tenant_id_map: Dict[int, int] = {}  # index (1..10) -> tenant_id

        for t_def in TENANT_DEFINITIONS:
            idx = t_def["index"]
            b_name = t_def["business_name"].strip()
            c_email = t_def["contact_email"].strip().lower()

            # Check if tenant already exists by tenant_id, business name, or contact email
            lookup_query = f"""
                SELECT tenant_id FROM {tenants_table}
                WHERE tenant_id = :idx OR lower(business_name) = :b_name OR lower(contact_email) = :c_email
                LIMIT 1
            """
            cursor.execute(lookup_query, {"idx": idx, "b_name": b_name.lower(), "c_email": c_email})
            existing_tenant = cursor.fetchone()

            if existing_tenant:
                tenant_id = int(existing_tenant[0])
                logger.info(
                    "Tenant [%d/10] '%s' already exists (tenant_id=%d). Updating metadata...",
                    idx,
                    b_name,
                    tenant_id,
                )
                update_query = f"""
                    UPDATE {tenants_table}
                    SET business_name = :business_name,
                        industry = :industry,
                        contact_person_name = :contact_person_name,
                        phone_number = :phone_number,
                        address_line1 = :address_line1,
                        address_line2 = :address_line2,
                        city = :city,
                        state = :state,
                        postal_code = :postal_code,
                        country = :country,
                        website_url = :website_url,
                        tax_id = :tax_id,
                        is_active = true
                    WHERE tenant_id = :tenant_id
                """
                cursor.execute(
                    update_query,
                    {
                        "tenant_id": tenant_id,
                        "business_name": b_name,
                        "industry": t_def["industry"],
                        "contact_person_name": t_def["contact_person_name"],
                        "phone_number": t_def["phone_number"],
                        "address_line1": t_def["address_line1"],
                        "address_line2": t_def["address_line2"],
                        "city": t_def["city"],
                        "state": t_def["state"],
                        "postal_code": t_def["postal_code"],
                        "country": t_def["country"],
                        "website_url": t_def["website_url"],
                        "tax_id": t_def["tax_id"],
                    },
                )
            else:
                logger.info("Inserting Tenant [%d/10] '%s'...", idx, b_name)
                insert_query = f"""
                    INSERT INTO {tenants_table} (
                        business_name,
                        industry,
                        contact_email,
                        created_by,
                        created_at,
                        is_active,
                        contact_person_name,
                        phone_number,
                        address_line1,
                        address_line2,
                        city,
                        state,
                        postal_code,
                        country,
                        website_url,
                        tax_id
                    ) VALUES (
                        :business_name,
                        :industry,
                        :contact_email,
                        NULL,
                        current_timestamp(),
                        true,
                        :contact_person_name,
                        :phone_number,
                        :address_line1,
                        :address_line2,
                        :city,
                        :state,
                        :postal_code,
                        :country,
                        :website_url,
                        :tax_id
                    )
                """
                cursor.execute(
                    insert_query,
                    {
                        "business_name": b_name,
                        "industry": t_def["industry"],
                        "contact_email": c_email,
                        "contact_person_name": t_def["contact_person_name"],
                        "phone_number": t_def["phone_number"],
                        "address_line1": t_def["address_line1"],
                        "address_line2": t_def["address_line2"],
                        "city": t_def["city"],
                        "state": t_def["state"],
                        "postal_code": t_def["postal_code"],
                        "country": t_def["country"],
                        "website_url": t_def["website_url"],
                        "tax_id": t_def["tax_id"],
                    },
                )

                # Fetch newly generated tenant_id
                cursor.execute(
                    f"SELECT tenant_id FROM {tenants_table} WHERE lower(business_name) = :b_name LIMIT 1",
                    {"b_name": b_name.lower()},
                )
                new_row = cursor.fetchone()
                if not new_row:
                    raise RuntimeError(f"Failed to retrieve tenant_id for created tenant '{b_name}'")
                tenant_id = int(new_row[0])
                logger.info("Created Tenant '%s' with tenant_id=%d", b_name, tenant_id)

            tenant_id_map[idx] = tenant_id

        # ---------------------------------------------------------------------
        # STEP 2: Upsert 10 SMB Owner Users
        # ---------------------------------------------------------------------
        logger.info("Upserting 10 SMB Owner user accounts...")
        smb_users_info: List[Dict[str, Any]] = []

        for t_def in TENANT_DEFINITIONS:
            idx = t_def["index"]
            tenant_id = tenant_id_map[idx]
            email = f"smb-owner-{idx}@helios-test.dev"
            name = t_def["contact_person_name"]
            phone = t_def["phone_number"]

            cursor.execute(
                f"SELECT user_id FROM {users_table} WHERE lower(email) = :email LIMIT 1",
                {"email": email.lower()},
            )
            existing_user = cursor.fetchone()

            if existing_user:
                user_id = int(existing_user[0])
                logger.info("SMB Owner [%d/10] '%s' exists (user_id=%d). Updating credentials...", idx, email, user_id)
                update_query = f"""
                    UPDATE {users_table}
                    SET tenant_id = :tenant_id,
                        name = :name,
                        password_hash = :password_hash,
                        role = 'smb_owner',
                        phone_number = :phone_number,
                        must_change_password = false,
                        is_active = true
                    WHERE user_id = :user_id
                """
                cursor.execute(
                    update_query,
                    {
                        "user_id": user_id,
                        "tenant_id": tenant_id,
                        "name": name,
                        "password_hash": password_hash,
                        "phone_number": phone,
                    },
                )
            else:
                logger.info("Inserting SMB Owner [%d/10] '%s'...", idx, email)
                ensure_no_active_owner(tenant_id, cursor=cursor)
                insert_query = f"""
                    INSERT INTO {users_table} (
                        tenant_id,
                        name,
                        email,
                        password_hash,
                        role,
                        phone_number,
                        staff_id,
                        designation,
                        must_change_password,
                        is_active,
                        created_at
                    ) VALUES (
                        :tenant_id,
                        :name,
                        :email,
                        :password_hash,
                        'smb_owner',
                        :phone_number,
                        NULL,
                        NULL,
                        false,
                        true,
                        current_timestamp()
                    )
                """
                cursor.execute(
                    insert_query,
                    {
                        "tenant_id": tenant_id,
                        "name": name,
                        "email": email.lower(),
                        "password_hash": password_hash,
                        "phone_number": phone,
                    },
                )
                cursor.execute(
                    f"SELECT user_id FROM {users_table} WHERE lower(email) = :email LIMIT 1",
                    {"email": email.lower()},
                )
                user_row = cursor.fetchone()
                user_id = int(user_row[0]) if user_row else 0

            smb_users_info.append({
                "email": email,
                "role": "smb_owner",
                "tenant_name": t_def["business_name"],
                "tenant_id": tenant_id,
                "ingestion_method": t_def["ingestion_method"],
            })

        # ---------------------------------------------------------------------
        # STEP 3: Upsert 5 Team Member Users & Tenant Assignments
        # ---------------------------------------------------------------------
        logger.info("Upserting 5 Team Member user accounts and assignments...")
        team_members_info: List[Dict[str, Any]] = []

        for tm_def in TEAM_MEMBER_DEFINITIONS:
            tm_idx = tm_def["index"]
            email = tm_def["email"]
            name = tm_def["name"]
            phone = tm_def["phone_number"]
            staff_id = tm_def["staff_id"]
            designation = tm_def["designation"]
            assigned_tenant_indices = tm_def["tenant_indices"]
            assigned_tenant_ids = [tenant_id_map[i] for i in assigned_tenant_indices]

            cursor.execute(
                f"SELECT user_id FROM {users_table} WHERE lower(email) = :email LIMIT 1",
                {"email": email.lower()},
            )
            existing_user = cursor.fetchone()

            if existing_user:
                user_id = int(existing_user[0])
                logger.info("Team Member [%d/5] '%s' exists (user_id=%d). Updating details...", tm_idx, email, user_id)
                update_query = f"""
                    UPDATE {users_table}
                    SET tenant_id = NULL,
                        name = :name,
                        password_hash = :password_hash,
                        role = 'team_member',
                        phone_number = :phone_number,
                        staff_id = :staff_id,
                        designation = :designation,
                        must_change_password = false,
                        is_active = true
                    WHERE user_id = :user_id
                """
                cursor.execute(
                    update_query,
                    {
                        "user_id": user_id,
                        "name": name,
                        "password_hash": password_hash,
                        "phone_number": phone,
                        "staff_id": staff_id,
                        "designation": designation,
                    },
                )
            else:
                logger.info("Inserting Team Member [%d/5] '%s'...", tm_idx, email)
                insert_query = f"""
                    INSERT INTO {users_table} (
                        tenant_id,
                        name,
                        email,
                        password_hash,
                        role,
                        phone_number,
                        staff_id,
                        designation,
                        must_change_password,
                        is_active,
                        created_at
                    ) VALUES (
                        NULL,
                        :name,
                        :email,
                        :password_hash,
                        'team_member',
                        :phone_number,
                        :staff_id,
                        :designation,
                        false,
                        true,
                        current_timestamp()
                    )
                """
                cursor.execute(
                    insert_query,
                    {
                        "name": name,
                        "email": email.lower(),
                        "password_hash": password_hash,
                        "phone_number": phone,
                        "staff_id": staff_id,
                        "designation": designation,
                    },
                )
                cursor.execute(
                    f"SELECT user_id FROM {users_table} WHERE lower(email) = :email LIMIT 1",
                    {"email": email.lower()},
                )
                user_row = cursor.fetchone()
                user_id = int(user_row[0]) if user_row else 0

            # Assign 2 tenants in platform.team_assignments
            for tid in assigned_tenant_ids:
                check_assignment_query = f"""
                    SELECT count(*) FROM {assignments_table}
                    WHERE user_id = :user_id AND tenant_id = :tenant_id
                """
                cursor.execute(check_assignment_query, {"user_id": user_id, "tenant_id": tid})
                cnt = cursor.fetchone()[0]

                if cnt == 0:
                    cursor.execute(
                        f"""
                        INSERT INTO {assignments_table} (user_id, tenant_id, assigned_at)
                        VALUES (:user_id, :tenant_id, current_timestamp())
                        """,
                        {"user_id": user_id, "tenant_id": tid},
                    )
                    logger.info("Assigned tenant_id=%d to team member user_id=%d", tid, user_id)

            assigned_names = [
                TENANT_DEFINITIONS[i - 1]["business_name"] for i in assigned_tenant_indices
            ]
            team_members_info.append({
                "email": email,
                "role": "team_member",
                "assigned_tenants": f"Tenants {assigned_tenant_indices} ({', '.join(assigned_names)})",
                "designation": designation,
            })

        # ---------------------------------------------------------------------
        # STEP 4: Create API Keys for Tenants 8, 9, 10
        # ---------------------------------------------------------------------
        logger.info("Generating API keys for API Push tenants (Tenants 8, 9, 10)...")
        output_dir = REPO_ROOT / "scripts" / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        api_keys_file = output_dir / "api_keys.json"

        # Load existing saved keys if file exists to preserve raw keys across re-runs
        existing_keys_data: Dict[str, Any] = {}
        if api_keys_file.is_file():
            try:
                with open(api_keys_file, "r", encoding="utf-8") as f:
                    existing_keys_data = json.load(f)
            except Exception:
                existing_keys_data = {}

        saved_keys_by_tenant: Dict[int, Dict[str, Any]] = {}
        for item in existing_keys_data.get("keys", []):
            if "tenant_id" in item:
                saved_keys_by_tenant[int(item["tenant_id"])] = item

        generated_api_keys: List[Dict[str, Any]] = []

        for api_tenant_idx in [8, 9, 10]:
            target_tenant_id = tenant_id_map[api_tenant_idx]
            tenant_name = TENANT_DEFINITIONS[api_tenant_idx - 1]["business_name"]

            # Check if active key already exists in platform.api_keys
            cursor.execute(
                f"SELECT api_key_id, key_hash, key_prefix FROM {api_keys_table} WHERE tenant_id = :tenant_id AND is_active = true LIMIT 1",
                {"tenant_id": target_tenant_id},
            )
            existing_key_row = cursor.fetchone()

            # If existing raw key in file matches the hash in DB, reuse it
            reused_existing = False
            if existing_key_row and target_tenant_id in saved_keys_by_tenant:
                saved_info = saved_keys_by_tenant[target_tenant_id]
                candidate_raw = saved_info.get("api_key", "")
                if hash_api_key(candidate_raw) == existing_key_row[1]:
                    logger.info("Reusing existing verified raw API key for Tenant %d ('%s')", target_tenant_id, tenant_name)
                    generated_api_keys.append(saved_info)
                    reused_existing = True

            if not reused_existing:
                # Generate new key using existing cryptographic helper
                raw_key = generate_api_key()
                hashed = hash_api_key(raw_key)
                masked = mask_api_key(raw_key)

                # Revoke previous active keys if any
                cursor.execute(
                    f"UPDATE {api_keys_table} SET is_active = false WHERE tenant_id = :tenant_id",
                    {"tenant_id": target_tenant_id},
                )

                # Insert new hashed key record
                insert_key_query = f"""
                    INSERT INTO {api_keys_table} (tenant_id, key_hash, key_prefix, created_at, is_active)
                    VALUES (:tenant_id, :key_hash, :key_prefix, current_timestamp(), true)
                """
                cursor.execute(
                    insert_key_query,
                    {
                        "tenant_id": target_tenant_id,
                        "key_hash": hashed,
                        "key_prefix": masked,
                    },
                )

                key_entry = {
                    "tenant_id": target_tenant_id,
                    "tenant_index": api_tenant_idx,
                    "business_name": tenant_name,
                    "api_key": raw_key,
                    "masked_key": masked,
                    "key_hash": hashed,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                generated_api_keys.append(key_entry)
                logger.info("Generated new API key for Tenant %d ('%s'): %s", target_tenant_id, tenant_name, masked)

        # Write raw keys to git-ignored output file
        with open(api_keys_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "note": "CONFIDENTIAL: Raw tenant API keys generated for local integration testing. Never commit this file.",
                    "keys": generated_api_keys,
                },
                f,
                indent=2,
            )
        logger.info("Raw API keys successfully written to '%s'", api_keys_file)

    # -------------------------------------------------------------------------
    # STEP 5: Print Formatted Summary Table
    # -------------------------------------------------------------------------
    print("\n" + "=" * 115)
    print(" HELIOS PLATFORM - TEST ACCOUNTS & TENANT SEEDING SUMMARY")
    print("=" * 115)
    print(f"{'User Email':<32} | {'Role':<12} | {'Tenant ID & Name / Scope':<38} | {'Planned Ingestion Method'}")
    print("-" * 115)

    # 1. Print SMB Owners
    for u in smb_users_info:
        tenant_str = f"#{u['tenant_id']} {u['tenant_name']}"
        print(f"{u['email']:<32} | {u['role']:<12} | {tenant_str:<38} | {u['ingestion_method']}")

    print("-" * 115)

    # 2. Print Team Members
    for tm in team_members_info:
        print(f"{tm['email']:<32} | {tm['role']:<12} | {tm['assigned_tenants']:<38} | Operations Review & Support")

    print("=" * 115)
    print("Authentication Note:")
    print(f"  - Password for all test accounts : (Read from TEST_ACCOUNT_PASSWORD environment variable)")
    print(f"  - First-login change password    : must_change_password = false (Test accounts can log in directly)")
    print(f"  - Raw API Keys (Tenants 8, 9, 10): Saved to '{api_keys_file}' (git-ignored)")
    print("=" * 115 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(seed_accounts())
