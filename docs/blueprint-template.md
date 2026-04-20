# Day 13 Observability Lab Report

> **Instruction**: Fill in all sections below. This report is designed to be parsed by an automated grading assistant. Ensure all tags (e.g., `[GROUP_NAME]`) are preserved.

## 1. Team Metadata
- [GROUP_NAME]: Solo-HaiNinh
- [REPO_URL]: https://github.com/haininh2311/Lab13-Observability
- [MEMBERS]:
  - Member A: Ning | Role: Logging & PII
  - Member B: Ning | Role: Tracing & Enrichment
  - Member C: Ning | Role: SLO & Alerts
  - Member D: Ning | Role: Load Test & Dashboard
  - Member E: Ning | Role: Demo & Report

---

## 2. Group Performance (Auto-Verified)
- [VALIDATE_LOGS_FINAL_SCORE]: 100/100
- [TOTAL_TRACES_COUNT]: 10+
- [PII_LEAKS_FOUND]: 0

---

## 3. Technical Evidence (Group)

### 3.1 Logging & Tracing
- [EVIDENCE_CORRELATION_ID_SCREENSHOT]: docs/screenshots/correlation_id.png
- [EVIDENCE_PII_REDACTION_SCREENSHOT]: docs/screenshots/pii_redaction.png
- [EVIDENCE_TRACE_WATERFALL_SCREENSHOT]: docs/screenshots/trace_waterfall.png
- [TRACE_WATERFALL_EXPLANATION]: The trace waterfall shows 5 child spans nested under the root `agent.run` span: `classify_topic` (< 1ms, keyword matching), `search_docs` (< 5ms, corpus scoring), `explain` (2–5s, gpt-4o-mini LLM call — the dominant span), `generate_quiz` (1–3s, second LLM call), and `format_response` (< 1ms, string concat). The `explain` span is the most interesting: it carries `tokens_in`, `tokens_out`, and `cost_usd` metadata, making it easy to attribute cost to individual requests.

### 3.2 Dashboard & SLOs
- [DASHBOARD_6_PANELS_SCREENSHOT]: docs/screenshots/dashboard_6panels.png
- [SLO_TABLE]:
| SLI | Target | Window | Current Value |
|---|---:|---|---:|
| Latency P95 | < 8000ms | 28d | ~4200ms |
| Error Rate | < 2% | 28d | 0% |
| Cost Budget | < $1.00/day | 1d | ~$0.003/day |
| Quality Score | > 0.70 avg | 28d | ~0.80 |

### 3.3 Alerts & Runbook
- [ALERT_RULES_SCREENSHOT]: docs/screenshots/alert_rules.png
- [SAMPLE_RUNBOOK_LINK]: docs/alerts.md

---

## 4. Incident Response (Group)
- [SCENARIO_NAME]: rag_slow
- [SYMPTOMS_OBSERVED]: P95 latency jumped from ~4s to ~7s after enabling the incident. Dashboard latency panel crossed the 8000ms SLO line. Traffic throughput dropped as requests queued.
- [ROOT_CAUSE_PROVED_BY]: Langfuse trace showed the `search_docs` span taking 2500ms (normally < 5ms). Log line: `{"event": "request_received", "correlation_id": "req-XXXXXXXX", "latency_ms": 7312, "level": "info"}` — the extra 2.5s sleep in `study_graph.py:search_docs` when `INCIDENT_STATE["rag_slow"] == True` was directly visible in the span duration.
- [FIX_ACTION]: Called `POST /incidents/rag_slow/disable` via `inject_incident.py --scenario rag_slow --disable`. Verified next request returned to normal latency (~4s) and span duration dropped to < 5ms.
- [PREVENTIVE_MEASURE]: Add a circuit breaker / timeout on the vector store call (e.g., `asyncio.wait_for(..., timeout=1.0)`). Alert `high_latency_p95` (threshold 15000ms) triggers on-call to investigate. In production, use a fallback to cached docs when retrieval exceeds 500ms.

---

## 5. Individual Contributions & Evidence

### [MEMBER_A_NAME] Ning — Logging & PII
- [TASKS_COMPLETED]: Implemented `app/middleware.py` (correlation ID middleware — generate UUID, bind to structlog contextvars, propagate in response headers). Implemented `app/pii.py` (6 PII regex patterns: email, phone_vn, CCCD, credit card, passport, vn_address; `scrub_text()`, `hash_user_id()`). Wired `scrub_event` processor into `app/logging_config.py`. Validated with `scripts/validate_logs.py` — 100/100, 0 PII leaks.
- [EVIDENCE_LINK]: https://github.com/haininh2311/Lab13-Observability/commit/e890059

### [MEMBER_B_NAME] Ning — Tracing & Enrichment
- [TASKS_COMPLETED]: Implemented `app/tracing.py` (Langfuse v3 `observe` + `get_client()` with graceful dummy fallback). Added `@observe()` decorators to all 5 nodes in `app/study_graph.py` for per-node child spans. Added `langfuse_context.update_current_trace/span()` in `app/agent.py` with user_id_hash, session_id, cost, quality metadata. Added `langfuse_context.flush()` in chat endpoint to ensure spans export in web server context.
- [EVIDENCE_LINK]: https://github.com/haininh2311/Lab13-Observability/commit/e890059

### [MEMBER_C_NAME] Ning — SLO & Alerts
- [TASKS_COMPLETED]: Defined 4 SLIs in `config/slo.yaml` (latency_p95 < 8000ms, error_rate < 2%, daily_cost < $1.00, quality_score > 0.70). Wrote 3 alert rules in `config/alert_rules.yaml` (high_latency_p95 > 15000ms P2, high_error_rate > 5% P1, cost_budget_spike > $0.50 P2). Wrote runbooks in `docs/alerts.md` covering symptoms, first checks, and mitigation for each alert.
- [EVIDENCE_LINK]: https://github.com/haininh2311/Lab13-Observability/commit/e890059

### [MEMBER_D_NAME] Ning — Load Test & Dashboard
- [TASKS_COMPLETED]: Built `app/static/dashboard.html` — 6-panel Chart.js dashboard (latency P50/P95/P99, traffic, error rate, cost/request, tokens in/out, quality). Auto-refresh every 15s, SLO threshold lines, alert banners. Added `/metrics/history` endpoint and `HISTORY` deque in `app/metrics.py`. Updated `scripts/load_test.py` (timeout 60s, `--loops`, cost/token summary). Ran 10+ load test cycles to generate traces.
- [EVIDENCE_LINK]: https://github.com/haininh2311/Lab13-Observability/commit/e890059

### [MEMBER_E_NAME] Ning — Demo & Report
- [TASKS_COMPLETED]: Built `app/study_graph.py` — full LangGraph pipeline (5 nodes: classify_topic → search_docs → explain → generate_quiz → format_response) with ChatOpenAI gpt-4o-mini. Created `data/study_corpus.json` (24 CS docs, 6 topics). Integrated incident toggles (rag_slow, tool_fail, cost_spike). Performed live incident response demo: enabled `rag_slow`, observed latency spike on dashboard, traced root cause in Langfuse waterfall, disabled incident, confirmed recovery.
- [EVIDENCE_LINK]: https://github.com/haininh2311/Lab13-Observability/commit/e890059

---

## 6. Bonus Items (Optional)
- [BONUS_COST_OPTIMIZATION]: gpt-4o-mini selected over gpt-4o (10× cheaper: $0.15/1M input vs $1.50/1M). Word limit capped at 300 tokens in normal mode, only raised to 800 in `cost_spike` incident for comparison. Estimated 70% cost reduction vs gpt-4o at same quality threshold. Evidence: `app/study_graph.py` `explain()` node + `_estimate_cost()` in `app/agent.py`.
- [BONUS_AUDIT_LOGS]: All requests logged to `data/logs.jsonl` in structured JSON (structlog). Fields include `correlation_id`, `user_id_hash` (SHA-256 truncated), `session_id`, `feature`, `model`, `latency_ms`, `tokens_in`, `tokens_out`, `cost_usd`. PII scrubbed before write. Log schema validated against `config/logging_schema.json`.
- [BONUS_CUSTOM_METRIC]: Added `quality_score` as a custom metric (heuristic: +0.2 if docs retrieved, +0.1 if answer > 100 chars, +0.1 if question keywords in answer, −0.2 if PII leaked through). Tracked in `app/metrics.py` QUALITY_SCORES list and exposed in `/metrics` snapshot and dashboard quality panel.
