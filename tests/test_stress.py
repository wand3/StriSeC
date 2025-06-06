#!/usr/bin/env python3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from client import query_server  # or from src.ssl_client import send_query
from src.server import handle_client
from src.config_loader import load_client_config
from pathlib import Path

# project root by walking up from this script’s directory
project_root = Path(__file__).resolve().parent.parent

# Build the config path relative to that root
config_path = project_root / "config" / "client_config.ini"

# Resolve to an absolute path, to be extra safe
config_path = config_path.resolve()

# Load your client settings (host, port, SSL, etc.)
CLIENT_CFG = load_client_config(str(config_path))
TEST_QUERY = "4;0;1;28;0;7;5;9;"


def worker_send(query: str) -> bool:
    """
    Sends a single query with client.
    Returns True on a valid 'FOUND' response, False otherwise.
    """
    try:
        resp = query_server(CLIENT_CFG['host'], CLIENT_CFG['port'], query)
        # Adjust this if your client returns full strings
        return "EXISTS" in resp.upper()
    except Exception:
        return False


def run_stress_test(qps: int, duration_sec: float) -> dict:
    """
    Fire `qps` queries per second for `duration_sec` seconds.
    Returns counts of successes and failures.
    """
    end_time = time.time() + duration_sec
    successes = 0
    failures = 0

    while time.time() < end_time:
        with ThreadPoolExecutor(max_workers=qps) as pool:
            futures = [pool.submit(worker_send, TEST_QUERY) for _ in range(qps)]
            # Wait _up to_ 5 seconds for each future to finish
            for fut in as_completed(futures, timeout=10):
                if fut.done():
                    successes += 1
                else:
                    failures += 1
        # Sleep so that we send the next batch roughly 1s later
        time.sleep(1)

    return {"qps": qps, "successes": successes, "failures": failures}


def main():
    # Define the QPS levels you want to test
    qps_levels = [5, 10, 20, 50, 100, 200, 500, 1000, 5000, 10000, 20000, 50000]
    duration = 10  # seconds per level

    print(f"Running stress test for {duration}s at varying QPS...")
    print(" QPS | Successes | Failures | Success Rate")
    print("-----+-----------+----------+-------------")

    for qps in qps_levels:
        result = run_stress_test(qps, duration)
        total = result["successes"] + result["failures"]
        rate = result["successes"] / total * 100 if total else 0
        print(f"{qps:4d} | {result['successes']:9d} | {result['failures']:8d} | {rate:11.1f}%")


if __name__ == "__main__":
    main()
