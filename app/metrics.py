from __future__ import annotations

import datetime
from collections import Counter, deque
from statistics import mean

REQUEST_LATENCIES: list[int] = []
REQUEST_COSTS: list[float] = []
REQUEST_TOKENS_IN: list[int] = []
REQUEST_TOKENS_OUT: list[int] = []
ERRORS: Counter[str] = Counter()
TRAFFIC: int = 0
QUALITY_SCORES: list[float] = []
HISTORY: deque[dict] = deque(maxlen=120)

_prev_traffic: int = 0
_prev_cost: float = 0.0
_prev_tokens_in: int = 0
_prev_tokens_out: int = 0
_prev_errors: int = 0


def record_request(latency_ms: int, cost_usd: float, tokens_in: int, tokens_out: int, quality_score: float) -> None:
    global TRAFFIC
    TRAFFIC += 1
    REQUEST_LATENCIES.append(latency_ms)
    REQUEST_COSTS.append(cost_usd)
    REQUEST_TOKENS_IN.append(tokens_in)
    REQUEST_TOKENS_OUT.append(tokens_out)
    QUALITY_SCORES.append(quality_score)
    _append_history()


def _append_history() -> None:
    global _prev_traffic, _prev_cost, _prev_tokens_in, _prev_tokens_out, _prev_errors

    total_errors = sum(ERRORS.values())
    current_cost = sum(REQUEST_COSTS)
    current_tokens_in = sum(REQUEST_TOKENS_IN)
    current_tokens_out = sum(REQUEST_TOKENS_OUT)

    snap = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "traffic_total": TRAFFIC,
        "traffic_window": TRAFFIC - _prev_traffic,
        "latency_p50": percentile(REQUEST_LATENCIES, 50),
        "latency_p95": percentile(REQUEST_LATENCIES, 95),
        "latency_p99": percentile(REQUEST_LATENCIES, 99),
        "error_rate_pct": round(total_errors / TRAFFIC * 100, 2) if TRAFFIC else 0.0,
        "cost_total_usd": round(current_cost, 6),
        "cost_window_usd": round(current_cost - _prev_cost, 6),
        "tokens_in_total": current_tokens_in,
        "tokens_out_total": current_tokens_out,
        "tokens_in_window": current_tokens_in - _prev_tokens_in,
        "tokens_out_window": current_tokens_out - _prev_tokens_out,
        "quality_avg": round(mean(QUALITY_SCORES), 4) if QUALITY_SCORES else 0.0,
        "errors_total": total_errors,
    }
    HISTORY.append(snap)

    _prev_traffic = TRAFFIC
    _prev_cost = current_cost
    _prev_tokens_in = current_tokens_in
    _prev_tokens_out = current_tokens_out
    _prev_errors = total_errors


def record_error(error_type: str) -> None:
    ERRORS[error_type] += 1


def percentile(values: list[int], p: int) -> float:
    if not values:
        return 0.0
    items = sorted(values)
    idx = max(0, min(len(items) - 1, round((p / 100) * len(items) + 0.5) - 1))
    return float(items[idx])


def snapshot() -> dict:
    return {
        "traffic": TRAFFIC,
        "latency_p50": percentile(REQUEST_LATENCIES, 50),
        "latency_p95": percentile(REQUEST_LATENCIES, 95),
        "latency_p99": percentile(REQUEST_LATENCIES, 99),
        "avg_cost_usd": round(mean(REQUEST_COSTS), 6) if REQUEST_COSTS else 0.0,
        "total_cost_usd": round(sum(REQUEST_COSTS), 6),
        "tokens_in_total": sum(REQUEST_TOKENS_IN),
        "tokens_out_total": sum(REQUEST_TOKENS_OUT),
        "error_breakdown": dict(ERRORS),
        "error_rate_pct": round(sum(ERRORS.values()) / TRAFFIC * 100, 2) if TRAFFIC else 0.0,
        "quality_avg": round(mean(QUALITY_SCORES), 4) if QUALITY_SCORES else 0.0,
    }
