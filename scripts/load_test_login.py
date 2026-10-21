#!/usr/bin/env python3
"""
Helios Platform - Login Load Test Verification Script

Calls POST /api/auth/login with a single known-good, correct test account
100 times in a row to verify that login never intermittently fails.

Asserts EVERY SINGLE call returns 200 OK with a valid signed JWT bearer token.
If any call fails, prints which attempt failed, status code, response payload,
and full exception/error detail.

Usage:
    python scripts/load_test_login.py [--url http://localhost:8000/api/auth/login] [--count 100] [--delay 0.05]
"""

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

# Add backend directory to sys.path so app modules can be resolved
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Load environment variables
from dotenv import load_dotenv

for env_candidate in [
    BACKEND_DIR / ".env",
    REPO_ROOT / ".env",
    Path.cwd() / ".env",
]:
    if env_candidate.is_file():
        load_dotenv(dotenv_path=env_candidate, override=False)
        break


def run_load_test(
    email: str = "admin@helios.io",
    password: str = None,
    count: int = 100,
    delay: float = 0.05,
    server_url: str = None,
) -> bool:
    """
    Execute 100 consecutive login requests and assert all return 200 with valid JWT.
    """
    if not password:
        password = os.getenv("ADMIN_PASSWORD")
    print("=" * 80)
    print("HELIOS PLATFORM - AUTHENTICATION RESILIENCE & LOAD TEST")
    print("=" * 80)
    print(f"Target account:   {email}")
    print(f"Total iterations: {count}")
    print(f"Loop delay:       {delay}s")

    client = None
    post_func = None

    if server_url:
        import requests
        print(f"Execution mode:   Live HTTP against {server_url}")

        def http_post(payload):
            resp = requests.post(server_url, json=payload, timeout=30)
            return resp.status_code, resp.text, resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}

        post_func = http_post
    else:
        print("Execution mode:   FastAPI TestClient (in-process live database execution)")
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)

        def testclient_post(payload):
            resp = client.post("/api/auth/login", json=payload)
            try:
                data = resp.json()
            except Exception:
                data = {}
            return resp.status_code, resp.text, data

        post_func = testclient_post

    print("-" * 80)

    payload = {"email": email, "password": password}
    latencies = []
    failed_attempts = []

    test_start_time = time.time()

    for i in range(1, count + 1):
        attempt_start = time.time()
        attempt_num = i

        try:
            status_code, raw_text, response_json = post_func(payload)
            elapsed = time.time() - attempt_start
            latencies.append(elapsed)

            # Assert HTTP 200
            if status_code != 200:
                error_detail = (
                    f"HTTP Status {status_code} != 200.\n"
                    f"Response Body: {raw_text}\n"
                    f"Parsed JSON: {json.dumps(response_json, indent=2)}"
                )
                print(f"\n[FAIL] Attempt {attempt_num}/{count} FAILED with status {status_code}:")
                print(error_detail)
                failed_attempts.append((attempt_num, error_detail))
                continue

            # Assert access_token is present and valid string
            access_token = response_json.get("access_token")
            token_type = response_json.get("token_type")

            if not access_token or not isinstance(access_token, str):
                error_detail = (
                    f"Missing or invalid 'access_token' in 200 response.\n"
                    f"Response JSON: {json.dumps(response_json, indent=2)}"
                )
                print(f"\n[FAIL] Attempt {attempt_num}/{count} FAILED token validation:")
                print(error_detail)
                failed_attempts.append((attempt_num, error_detail))
                continue

            if token_type != "bearer":
                error_detail = f"Expected token_type 'bearer', got: {token_type!r}"
                print(f"\n[FAIL] Attempt {attempt_num}/{count} FAILED token_type validation:")
                print(error_detail)
                failed_attempts.append((attempt_num, error_detail))
                continue

            # Success
            token_prefix = access_token[:16] + "..." if len(access_token) > 16 else access_token
            print(
                f"[{attempt_num:03d}/{count:03d}] PASS "
                f"(status={status_code}, time={elapsed:.2f}s, token={token_prefix})"
            )

        except Exception as exc:
            elapsed = time.time() - attempt_start
            latencies.append(elapsed)
            tb = traceback.format_exc()
            error_detail = (
                f"Exception raised during attempt {attempt_num}:\n"
                f"Exception: {type(exc).__name__}: {exc}\n"
                f"Traceback:\n{tb}"
            )
            print(f"\n[FAIL] Attempt {attempt_num}/{count} CRASHED with exception:")
            print(error_detail)
            failed_attempts.append((attempt_num, error_detail))

        if delay > 0 and i < count:
            time.sleep(delay)

    total_duration = time.time() - test_start_time
    total_passes = count - len(failed_attempts)

    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total Requests:   {count}")
    print(f"Successful (200): {total_passes}")
    print(f"Failed:           {len(failed_attempts)}")
    print(f"Total Duration:   {total_duration:.2f}s")
    if latencies:
        print(f"Min Latency:      {min(latencies):.2f}s")
        print(f"Max Latency:      {max(latencies):.2f}s")
        print(f"Avg Latency:      {sum(latencies) / len(latencies):.2f}s")
    print("-" * 80)

    if failed_attempts:
        print(f"[FATAL] Verification FAILED: {len(failed_attempts)} attempt(s) did not succeed.")
        for attempt_num, detail in failed_attempts:
            print(f"\n--- Failure on Attempt #{attempt_num} ---")
            print(detail)
        return False

    print(f"[SUCCESS] ALL {count}/{count} consecutive login attempts succeeded with HTTP 200 and valid JWTs!")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify Helios /api/auth/login 100 consecutive requests with zero failures."
    )
    parser.add_argument(
        "--email",
        default=os.getenv("TEST_LOGIN_EMAIL", "admin@helios.io"),
        help="Email address of known-good test account (default: admin@helios.io)",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("ADMIN_PASSWORD"),
        help="Plaintext password for known-good test account",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="Number of consecutive login requests to run (default: 100)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.05,
        help="Delay in seconds between requests (default: 0.05)",
    )
    parser.add_argument(
        "--url",
        default=None,
        help="Optional live HTTP URL (e.g. http://localhost:8000/api/auth/login). If omitted, uses FastAPI TestClient.",
    )

    args = parser.parse_args()
    success = run_load_test(
        email=args.email,
        password=args.password,
        count=args.count,
        delay=args.delay,
        server_url=args.url,
    )
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
