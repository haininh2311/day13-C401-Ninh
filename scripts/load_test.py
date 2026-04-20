from __future__ import annotations

import argparse
import concurrent.futures
import json
import time
from pathlib import Path

import httpx

BASE_URL = "http://127.0.0.1:8000"
QUERIES = Path("data/sample_queries.jsonl")


def send_request(client: httpx.Client, payload: dict) -> dict:
    try:
        start = time.perf_counter()
        r = client.post(f"{BASE_URL}/chat", json=payload)
        elapsed = (time.perf_counter() - start) * 1000
        if r.status_code == 200:
            d = r.json()
            cid = d.get("correlation_id", "?")
            tokens_in = d.get("tokens_in", 0)
            tokens_out = d.get("tokens_out", 0)
            cost = d.get("cost_usd", 0)
            print(f"[{r.status_code}] {cid} | {payload['feature']} | {elapsed:.0f}ms | {tokens_in}in/{tokens_out}out | ${cost:.5f}")
            return {"ok": True, "latency_ms": elapsed, "cost_usd": cost, "tokens_in": tokens_in, "tokens_out": tokens_out}
        else:
            print(f"[{r.status_code}] {payload['feature']} | {elapsed:.0f}ms | ERROR: {r.text[:80]}")
            return {"ok": False}
    except Exception as e:
        print(f"[ERR] {payload['feature']} | {e}")
        return {"ok": False}


def main() -> None:
    parser = argparse.ArgumentParser(description="Load test for Study Assistant agent")
    parser.add_argument("--concurrency", type=int, default=1, help="Concurrent requests")
    parser.add_argument("--loops", type=int, default=1, help="Repeat all queries N times")
    args = parser.parse_args()

    lines = [line for line in QUERIES.read_text(encoding="utf-8").splitlines() if line.strip()]
    payloads = [json.loads(line) for line in lines] * args.loops

    print(f"Sending {len(payloads)} requests (concurrency={args.concurrency}, loops={args.loops})...\n")
    results = []
    t0 = time.perf_counter()

    with httpx.Client(timeout=60.0) as client:
        if args.concurrency > 1:
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
                futures = [executor.submit(send_request, client, p) for p in payloads]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]
        else:
            for p in payloads:
                results.append(send_request(client, p))

    total_s = time.perf_counter() - t0
    ok = [r for r in results if r.get("ok")]
    fail = len(results) - len(ok)
    avg_latency = sum(r["latency_ms"] for r in ok) / len(ok) if ok else 0
    total_cost = sum(r["cost_usd"] for r in ok)
    total_tokens_in = sum(r["tokens_in"] for r in ok)
    total_tokens_out = sum(r["tokens_out"] for r in ok)

    print(f"\n--- Summary ---")
    print(f"Total: {len(results)} | OK: {len(ok)} | Failed: {fail}")
    print(f"Wall time: {total_s:.1f}s | Avg latency: {avg_latency:.0f}ms")
    print(f"Tokens: {total_tokens_in} in / {total_tokens_out} out | Total cost: ${total_cost:.5f}")


if __name__ == "__main__":
    main()
