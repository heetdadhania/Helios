import os
import sys
import time
from typing import Dict, Any, Tuple
from fastapi.testclient import TestClient

# Ensure backend root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.security import create_access_token

ENDPOINTS = [
    ("/api/dashboard/revenue-trend", "Revenue Trend"),
    ("/api/dashboard/top-products", "Top Products"),
    ("/api/dashboard/late-delivery-risk", "Late Delivery Risk"),
    ("/api/dashboard/discount-vs-profit", "Discount vs Profit"),
    ("/api/dashboard/shipping-mode-comparison", "Shipping Mode Comparison"),
]

def run_benchmark():
    # User 3 is owner@apexconsumer.com, role=smb_owner, tenant_id=1
    token = create_access_token(user_id=3, role="smb_owner", tenant_id=1)
    headers = {"Authorization": f"Bearer {token}"}
    client = TestClient(app)

    print("=" * 80)
    print("STEP 1: MEASURING BASELINE (BEFORE ANY FIXES)")
    print("=" * 80)

    results = {"cold": {}, "warm": {}}

    print("\n--- PHASE 1: COLD RUN (First call after app starts) ---")
    for path, name in ENDPOINTS:
        t_req_start = time.perf_counter()
        resp = client.get(path, headers=headers)
        t_req = time.perf_counter() - t_req_start

        if resp.status_code != 200:
            print(f"ERROR: {name} ({path}) failed with status {resp.status_code}: {resp.text}")
            continue

        conn = float(resp.headers.get("X-Timing-Connection", "0.0"))
        query = float(resp.headers.get("X-Timing-Query", "0.0"))
        ser = float(resp.headers.get("X-Timing-Serialization", "0.0"))
        total = float(resp.headers.get("X-Timing-Total", "0.0"))

        results["cold"][name] = {
            "conn": conn,
            "query": query,
            "serialization": ser,
            "endpoint_total": total,
            "roundtrip": t_req,
        }
        print(
            f"COLD | {name:<26} | (a) Conn: {conn:.4f}s | (b) Query: {query:.4f}s | (c) Ser: {ser:.4f}s | Endpoint Total: {total:.4f}s | Roundtrip: {t_req:.4f}s"
        )

    print("\n--- PHASE 2: WARM RUN (Immediately calling again) ---")
    for path, name in ENDPOINTS:
        t_req_start = time.perf_counter()
        resp = client.get(path, headers=headers)
        t_req = time.perf_counter() - t_req_start

        if resp.status_code != 200:
            print(f"ERROR: {name} ({path}) failed with status {resp.status_code}: {resp.text}")
            continue

        conn = float(resp.headers.get("X-Timing-Connection", "0.0"))
        query = float(resp.headers.get("X-Timing-Query", "0.0"))
        ser = float(resp.headers.get("X-Timing-Serialization", "0.0"))
        total = float(resp.headers.get("X-Timing-Total", "0.0"))

        results["warm"][name] = {
            "conn": conn,
            "query": query,
            "serialization": ser,
            "endpoint_total": total,
            "roundtrip": t_req,
        }
        print(
            f"WARM | {name:<26} | (a) Conn: {conn:.4f}s | (b) Query: {query:.4f}s | (c) Ser: {ser:.4f}s | Endpoint Total: {total:.4f}s | Roundtrip: {t_req:.4f}s"
        )

    print("\n" + "=" * 80)
    print("BASELINE MEASUREMENT SUMMARY TABLE")
    print("=" * 80)
    header = f"{'Endpoint':<26} | {'Run':<4} | {'(a) Conn (s)':<12} | {'(b) Query (s)':<13} | {'(c) Ser (s)':<11} | {'Total (s)':<9}"
    print(header)
    print("-" * len(header))
    for _, name in ENDPOINTS:
        c = results["cold"].get(name, {})
        w = results["warm"].get(name, {})
        print(
            f"{name:<26} | COLD | {c.get('conn', 0.0):<12.4f} | {c.get('query', 0.0):<13.4f} | {c.get('serialization', 0.0):<11.4f} | {c.get('endpoint_total', 0.0):<9.4f}"
        )
        print(
            f"{name:<26} | WARM | {w.get('conn', 0.0):<12.4f} | {w.get('query', 0.0):<13.4f} | {w.get('serialization', 0.0):<11.4f} | {w.get('endpoint_total', 0.0):<9.4f}"
        )
        print("-" * len(header))

    return results

if __name__ == "__main__":
    run_benchmark()
