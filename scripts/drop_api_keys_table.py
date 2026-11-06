import os
import sys
sys.path.insert(0, os.path.abspath("backend"))

from dotenv import load_dotenv
load_dotenv("backend/.env")

from app.db.base import get_databricks_connection

def drop_api_keys():
    print("Connecting to Databricks SQL endpoint...")
    conn = get_databricks_connection()
    cursor = conn.cursor()
    try:
        # 1. Confirm whether platform.api_keys exists
        cursor.execute("SHOW TABLES IN platform LIKE 'api_keys'")
        tables = cursor.fetchall()
        print(f"Tables matching 'api_keys' in platform: {tables}")

        # 2. Check pending_uploads for any rows with source_type = 'api_push'
        cursor.execute("SELECT COUNT(1) FROM platform.pending_uploads WHERE source_type = 'api_push'")
        count_row = cursor.fetchone()
        count = count_row[0] if count_row else 0
        print(f"Pending uploads with source_type='api_push': {count}")

        # 3. Drop platform.api_keys table
        print("Executing: DROP TABLE IF EXISTS platform.api_keys")
        cursor.execute("DROP TABLE IF EXISTS platform.api_keys")
        print("Successfully dropped platform.api_keys table!")

        # 4. Verify table is dropped
        cursor.execute("SHOW TABLES IN platform LIKE 'api_keys'")
        after = cursor.fetchall()
        print(f"Tables matching 'api_keys' after drop: {after}")

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    drop_api_keys()

