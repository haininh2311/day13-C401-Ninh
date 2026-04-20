from __future__ import annotations

import os
from typing import Any

try:
    from langfuse import get_client, observe  # noqa: F401

    langfuse_context = get_client()

except Exception:
    def observe(*args: Any, **kwargs: Any):  # type: ignore[misc]
        def decorator(func: Any) -> Any:
            return func
        return decorator

    class _DummyClient:
        def update_current_trace(self, **kwargs: Any) -> None:
            return None
        def update_current_span(self, **kwargs: Any) -> None:
            return None
        def get_current_trace_id(self) -> str | None:
            return None
        def flush(self) -> None:
            return None

    langfuse_context = _DummyClient()  # type: ignore[assignment]


def tracing_enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))
