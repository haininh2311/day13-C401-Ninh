from __future__ import annotations

import time
from dataclasses import dataclass

from . import metrics
from .pii import hash_user_id, summarize_text
from .study_graph import build_graph
from .tracing import langfuse_context, observe

@dataclass
class AgentResult:
    answer: str
    latency_ms: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    quality_score: float


class LabAgent:
    def __init__(self, model: str = "gpt-4o-mini") -> None:
        self.model = model
        self.graph = build_graph()

    @observe()
    def run(self, user_id: str, feature: str, session_id: str, message: str) -> AgentResult:
        started = time.perf_counter()

        result = self.graph.invoke({
            "question": message,
            "topic": "",
            "docs": [],
            "explanation": "",
            "quiz": "",
            "tokens_in": 0,
            "tokens_out": 0,
        })

        tokens_in: int = result["tokens_in"]
        tokens_out: int = result["tokens_out"]
        answer: str = result["explanation"]
        docs: list[str] = result["docs"]
        latency_ms = int((time.perf_counter() - started) * 1000)
        cost_usd = self._estimate_cost(tokens_in, tokens_out)
        quality_score = self._heuristic_quality(message, answer, docs)

        langfuse_context.update_current_trace(
            user_id=hash_user_id(user_id),
            session_id=session_id,
            tags=["lab", feature, self.model],
        )
        langfuse_context.update_current_span(
            metadata={
                "doc_count": len(docs),
                "topic": result.get("topic", ""),
                "query_preview": summarize_text(message),
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_usd": cost_usd,
                "quality_score": quality_score,
            },
        )

        metrics.record_request(
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            quality_score=quality_score,
        )

        return AgentResult(
            answer=answer,
            latency_ms=latency_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            quality_score=quality_score,
        )

    def _estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        # gpt-4o-mini: $0.15/1M input, $0.60/1M output
        return round((tokens_in / 1_000_000) * 0.15 + (tokens_out / 1_000_000) * 0.60, 8)

    def _heuristic_quality(self, question: str, answer: str, docs: list[str]) -> float:
        score = 0.5
        if docs:
            score += 0.2
        if len(answer) > 100:
            score += 0.1
        q_words = question.lower().split()[:3]
        if q_words and any(w in answer.lower() for w in q_words):
            score += 0.1
        if "[REDACTED" in answer:
            score -= 0.2
        return round(max(0.0, min(1.0, score)), 2)
