from __future__ import annotations

import json
import sys
from pathlib import Path

LOG_PATH = Path("data/logs.jsonl")
REQUIRED_FIELDS = {"ts", "level", "event"}
ENRICHMENT_FIELDS = {"user_id_hash", "session_id", "feature", "model", "correlation_id"}
EXPECTED_MODEL = "gpt-4o-mini"


def main() -> None:
    if not LOG_PATH.exists():
        print(f"Error: {LOG_PATH} not found. Run the app and send some requests first.")
        sys.exit(1)

    records = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if not records:
        print("Error: No valid JSON logs found in data/logs.jsonl")
        sys.exit(1)

    total = len(records)
    missing_required = 0
    missing_enrichment = 0
    wrong_model = 0
    pii_hits = []
    correlation_ids = set()
    response_logs = [r for r in records if r.get("event") == "response_sent"]
    has_cost = sum(1 for r in response_logs if r.get("cost_usd", 0) > 0)
    has_tokens = sum(1 for r in response_logs if r.get("tokens_in", 0) > 0)

    for rec in records:
        if not REQUIRED_FIELDS.issubset(rec.keys()):
            missing_required += 1

        if rec.get("service") == "api":
            if "correlation_id" not in rec or rec.get("correlation_id") == "MISSING":
                missing_required += 1
            if not ENRICHMENT_FIELDS.issubset(rec.keys()):
                missing_enrichment += 1
            model = rec.get("model", "")
            if model and model != EXPECTED_MODEL:
                wrong_model += 1

        raw = json.dumps(rec)
        if "@" in raw or "4111" in raw:
            pii_hits.append(rec.get("event", "unknown"))

        cid = rec.get("correlation_id")
        if cid and cid != "MISSING":
            correlation_ids.add(cid)

    print("--- Lab Verification Results ---")
    print(f"Total log records analyzed: {total}")
    print(f"Records with missing required fields: {missing_required}")
    print(f"Records with missing enrichment (context): {missing_enrichment}")
    print(f"Unique correlation IDs found: {len(correlation_ids)}")
    print(f"Potential PII leaks detected: {len(pii_hits)}")
    print(f"response_sent logs with cost: {has_cost}/{len(response_logs)}")
    print(f"response_sent logs with tokens: {has_tokens}/{len(response_logs)}")
    if wrong_model:
        print(f"Logs with unexpected model (not {EXPECTED_MODEL}): {wrong_model}")
    if pii_hits:
        print(f"  Events with leaks: {set(pii_hits)}")

    print("\n--- Grading Scorecard (Estimates) ---")
    score = 100

    if missing_required > 0:
        score -= 30
        print("- [FAILED] Basic JSON schema (missing ts/level/correlation_id)")
    else:
        print("+ [PASSED] Basic JSON schema")

    if len(correlation_ids) < 2:
        score -= 20
        print("- [FAILED] Correlation ID propagation (< 2 unique IDs)")
    else:
        print("+ [PASSED] Correlation ID propagation")

    if missing_enrichment > 0:
        score -= 20
        print("- [FAILED] Log enrichment (missing user_id_hash / session_id / model)")
    else:
        print("+ [PASSED] Log enrichment")

    if pii_hits:
        score -= 30
        print("- [FAILED] PII scrubbing (found @ or credit card number in logs)")
    else:
        print("+ [PASSED] PII scrubbing")

    if response_logs and has_cost == 0:
        score -= 5
        print("- [WARN] No cost_usd found in response_sent logs")
    else:
        print("+ [PASSED] Cost tracking in logs")

    if response_logs and has_tokens == 0:
        score -= 5
        print("- [WARN] No tokens_in found in response_sent logs")
    else:
        print("+ [PASSED] Token tracking in logs")

    print(f"\nEstimated Score: {max(0, score)}/100")


if __name__ == "__main__":
    main()
