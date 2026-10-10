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


# -----------------------------------------------------------------------------
# Configuration: 10 Realistic Diverse Tenants & Ingestion Method Mappings
# -----------------------------------------------------------------------------
TENANT_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "index": 1,
        "business_name": "Apex Consumer Goods",
        "industry": "Apparel",
        "contact_person_name": "Marcus Vance",
        "contact_email": "contact@apexconsumer.com",
        "phone_number": "+1 (415) 555-0142",
        "address_line1": "450 Sutter St",
        "address_line2": "Suite 700",
        "city": "San Francisco",
        "state": "California",
        "postal_code": "94108",
        "country": "USA",
        "website_url": "https://www.apexconsumer.com",
        "tax_id": "US-941829101",
        "ingestion_method": "File Upload (CSV/Excel)",
    },
    {
        "index": 2,
        "business_name": "Pacific Tech & Corporate",
        "industry": "Electronics",
        "contact_person_name": "Kenji Sato",
        "contact_email": "contact@pacifictech.jp",
        "phone_number": "+81 3 5555 0198",
        "address_line1": "1-8-1 Roppongi, Minato-ku",
        "address_line2": "Tower B, Level 14",
        "city": "Tokyo",
        "state": "Tokyo",
        "postal_code": "106-0032",
        "country": "Japan",
        "website_url": "https://www.pacifictech.jp",
        "tax_id": "JP-881920391",
        "ingestion_method": "File Upload (CSV/Excel)",
    },
    {
        "index": 3,
        "business_name": "Vanguard Home Office",
        "industry": "Home Goods",
        "contact_person_name": "Freja Lindqvist",
        "contact_email": "contact@vanguardhome.se",
        "phone_number": "+46 8 555 0123",
        "address_line1": "Drottninggatan 56",
        "address_line2": None,
        "city": "Stockholm",
        "state": "Stockholm",
        "postal_code": "111 21",
        "country": "Sweden",
        "website_url": "https://www.vanguardhome.se",
        "tax_id": "SE-5561234567",
        "ingestion_method": "File Upload (CSV/Excel)",
    },
    {
        "index": 4,
        "business_name": "Velvet Botanicals",
        "industry": "Beauty",
        "contact_person_name": "Chloe Dubois",
        "contact_email": "care@velvetbotanicals.fr",
        "phone_number": "+33 1 42 68 55 00",
        "address_line1": "14 Rue de la Paix",
        "address_line2": "Batiment C",
        "city": "Paris",
        "state": "Île-de-France",
        "postal_code": "75002",
        "country": "France",
        "website_url": "https://www.velvetbotanicals.fr",
        "tax_id": "FR-901827364",
        "ingestion_method": "File Upload (CSV/Excel)",
    },
    {
        "index": 5,
        "business_name": "Summit Peak Athletics",
        "industry": "Sports",
        "contact_person_name": "Lukas Weber",
        "contact_email": "contact@summitpeak.de",
        "phone_number": "+49 89 555 0177",
        "address_line1": "Maximilianstraße 35",
        "address_line2": None,
        "city": "Munich",
        "state": "Bavaria",
        "postal_code": "80539",
        "country": "Germany",
        "website_url": "https://www.summitpeak.de",
        "tax_id": "DE-312984712",
        "ingestion_method": "Database Connection (RDBMS - PostgreSQL)",
    },
    {
        "index": 6,
        "business_name": "Page & Quill Publishing",
        "industry": "Books",
        "contact_person_name": "Oliver Davies",
        "contact_email": "editorial@pageandquill.co.uk",
        "phone_number": "+44 20 7946 0912",
        "address_line1": "22 Bloomsbury Square",
        "address_line2": "Suite 4B",
        "city": "London",
        "state": "Greater London",
        "postal_code": "WC1A 2LS",
        "country": "United Kingdom",
        "website_url": "https://www.pageandquill.co.uk",
        "tax_id": "GB-771829103",
        "ingestion_method": "Database Connection (RDBMS - MySQL)",
    },
    {
        "index": 7,
        "business_name": "WonderKite Toyworks",
        "industry": "Toys",
        "contact_person_name": "Liam O'Connor",
        "contact_email": "play@wonderkitetoys.ca",
        "phone_number": "+1 (416) 555-0184",
        "address_line1": "350 Bay Street",
        "address_line2": "Floor 12",
        "city": "Toronto",
        "state": "Ontario",
        "postal_code": "M5H 2S6",
        "country": "Canada",
        "website_url": "https://www.wonderkitetoys.ca",
        "tax_id": "CA-819283746",
        "ingestion_method": "Database Connection (RDBMS - SQL Server)",
    },
    {
        "index": 8,
        "business_name": "Terra Verde Organics",
        "industry": "Grocery",
        "contact_person_name": "Sofia Rossi",
        "contact_email": "orders@terraverde.it",
        "phone_number": "+39 02 555 0166",
        "address_line1": "Via Montenapoleone 8",
        "address_line2": None,
        "city": "Milan",
        "state": "Lombardy",
        "postal_code": "20121",
        "country": "Italy",
        "website_url": "https://www.terraverde.it",
        "tax_id": "IT-481920394",
        "ingestion_method": "REST API Push",
    },
    {
        "index": 9,
        "business_name": "Luminary Fine Gems",
        "industry": "Jewelry",
        "contact_person_name": "Priya Sharma",
        "contact_email": "concierge@luminarygems.in",
        "phone_number": "+91 22 5555 0133",
        "address_line1": "Bandra Kurla Complex, Tower B",
        "address_line2": "Floor 9",
        "city": "Mumbai",
        "state": "Maharashtra",
        "postal_code": "400051",
        "country": "India",
        "website_url": "https://www.luminarygems.in",
        "tax_id": "IN-27AABCL1234F1Z5",
        "ingestion_method": "REST API Push",
    },
    {
        "index": 10,
        "business_name": "Paws & Trails Outfitters",
        "industry": "Pet Supplies",
        "contact_person_name": "Jack Campbell",
        "contact_email": "bark@pawsandtrails.com.au",
        "phone_number": "+61 2 9555 0144",
        "address_line1": "88 George Street, The Rocks",
        "address_line2": "Unit 3",
        "city": "Sydney",
        "state": "New South Wales",
        "postal_code": "2000",
        "country": "Australia",
        "website_url": "https://www.pawsandtrails.com.au",
        "tax_id": "AU-918273645",
        "ingestion_method": "REST API Push",
    },
]

# -----------------------------------------------------------------------------
# Configuration: 5 Team Members
# -----------------------------------------------------------------------------
TEAM_MEMBER_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "index": 1,
        "name": "Sarah Jenkins",
        "email": "team-member-1@helios-test.dev",
        "phone_number": "+1 (555) 011-1001",
        "staff_id": "TM-101",
        "designation": "Senior Ingestion Analyst",
        "tenant_indices": [1, 2],
    },
    {
        "index": 2,
        "name": "Alex Morgan",
        "email": "team-member-2@helios-test.dev",
        "phone_number": "+1 (555) 012-1002",
        "staff_id": "TM-102",
        "designation": "Data Quality Operations Lead",
        "tenant_indices": [3, 4],
    },
    {
        "index": 3,
        "name": "Michael Chen",
        "email": "team-member-3@helios-test.dev",
        "phone_number": "+1 (555) 013-1003",
        "staff_id": "TM-103",
        "designation": "Pipeline Integration Specialist",
        "tenant_indices": [5, 6],
    },
    {
        "index": 4,
        "name": "Amara Okafor",
        "email": "team-member-4@helios-test.dev",
        "phone_number": "+1 (555) 014-1004",
        "staff_id": "TM-104",
        "designation": "Customer Solutions Architect",
        "tenant_indices": [7, 8],
    },
    {
        "index": 5,
        "name": "Julian Rivera",
        "email": "team-member-5@helios-test.dev",
        "phone_number": "+1 (555) 015-1005",
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

            # Check if tenant already exists by business name or contact email
            lookup_query = f"""
                SELECT tenant_id FROM {tenants_table}
                WHERE lower(business_name) = :b_name OR lower(contact_email) = :c_email
                LIMIT 1
            """
            cursor.execute(lookup_query, {"b_name": b_name.lower(), "c_email": c_email})
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
                    SET industry = :industry,
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
