import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.db.base import databricks_cursor

TARGET_EMAILS = [
    "owner@apexconsumer.com",
    "owner@pacifictech.com",
    "owner@vanguardhome.com",
]

def main():
    with databricks_cursor() as cur:
        # 1. Fetch user rows
        email_list_str = ", ".join(f"'{e}'" for e in TARGET_EMAILS)
        cur.execute(f"SELECT user_id, tenant_id, name, email, role FROM `helios_catalog`.`platform`.`users` WHERE email IN ({email_list_str})")
        users = cur.fetchall()
        print(f"Found {len(users)} target users to remove/deactivate:")
        user_ids = []
        for u in users:
            uid, tid, name, email, role = u
            user_ids.append(uid)
            print(f"  User ID {uid}: {email} (Tenant {tid}, Role {role})")

        if not user_ids:
            print("No target users found.")
            return

        uids_str = ", ".join(str(uid) for uid in user_ids)

        # 2. Check references in platform.tenants
        cur.execute(f"SELECT tenant_id, business_name, created_by, assigned_team_member_id FROM `helios_catalog`.`platform`.`tenants` WHERE created_by IN ({uids_str}) OR assigned_team_member_id IN ({uids_str})")
        t_refs = cur.fetchall()
        print(f"References in platform.tenants: {len(t_refs)}")
        for r in t_refs:
            print(f"  Tenant {r[0]} ('{r[1]}'): created_by={r[2]}, assigned_team_member_id={r[3]}")

        # 3. Check references in platform.team_assignments
        cur.execute(f"SELECT user_id, tenant_id FROM `helios_catalog`.`platform`.`team_assignments` WHERE user_id IN ({uids_str})")
        ta_refs = cur.fetchall()
        print(f"References in platform.team_assignments: {len(ta_refs)}")

        # 4. Check references in platform.pending_uploads
        cur.execute(f"SELECT upload_id, tenant_id, uploaded_by FROM `helios_catalog`.`platform`.`pending_uploads` WHERE uploaded_by IN ({uids_str})")
        pu_refs = cur.fetchall()
        print(f"References in platform.pending_uploads: {len(pu_refs)}")

        # 5. Check references in platform.notification_log
        cur.execute(f"SELECT notification_id, tenant_id, user_id FROM `helios_catalog`.`platform`.`notification_log` WHERE user_id IN ({uids_str})")
        nl_refs = cur.fetchall()
        print(f"References in platform.notification_log: {len(nl_refs)}")

        # 6. Check references in platform.support_messages
        cur.execute(f"SELECT message_id, from_user_id, to_user_id FROM `helios_catalog`.`platform`.`support_messages` WHERE from_user_id IN ({uids_str}) OR to_user_id IN ({uids_str})")
        sm_refs = cur.fetchall()
        print(f"References in platform.support_messages: {len(sm_refs)}")

        total_refs = len(t_refs) + len(ta_refs) + len(pu_refs) + len(nl_refs) + len(sm_refs)
        print(f"Total reference count across all tables: {total_refs}")

        if total_refs == 0:
            print(f"Users are unreferenced! Deleting rows from platform.users for emails {TARGET_EMAILS}...")
            cur.execute(f"DELETE FROM `helios_catalog`.`platform`.`users` WHERE email IN ({email_list_str})")
            print("Successfully deleted target users.")
        else:
            print("Users ARE referenced. Deactivating them instead...")
            cur.execute(f"UPDATE `helios_catalog`.`platform`.`users` SET is_active = false WHERE email IN ({email_list_str})")
            print("Successfully deactivated target users.")

        # 7. Verification query
        print("\n--- Verification Query ---")
        cur.execute("SELECT count(*) FROM `helios_catalog`.`platform`.`users` WHERE role = 'smb_owner' AND is_active = true")
        active_smb = cur.fetchone()[0]
        cur.execute("SELECT count(DISTINCT tenant_id) FROM `helios_catalog`.`platform`.`users` WHERE role = 'smb_owner' AND is_active = true")
        distinct_smb_tenants = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM `helios_catalog`.`platform`.`users` WHERE role = 'team_member' AND is_active = true")
        active_tm = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM `helios_catalog`.`platform`.`users` WHERE role = 'admin' AND is_active = true")
        active_admin = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM `helios_catalog`.`platform`.`team_assignments`")
        assignment_count = cur.fetchone()[0]

        print(f"Active SMB Owners: {active_smb} (Distinct tenants: {distinct_smb_tenants})")
        print(f"Active Team Members: {active_tm}")
        print(f"Active Admins: {active_admin}")
        print(f"Team Assignments: {assignment_count}")

        # Detail of remaining SMB owners
        cur.execute("SELECT tenant_id, user_id, name, email, role, is_active FROM `helios_catalog`.`platform`.`users` WHERE role = 'smb_owner' ORDER BY tenant_id")
        for r in cur.fetchall():
            print(f"  Tenant {r[0]}: User {r[1]} ('{r[2]}', {r[3]}), active={r[5]}")

if __name__ == "__main__":
    main()
