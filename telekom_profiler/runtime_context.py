"""Request-scoped context for UI session (subscriber selection)."""

from __future__ import annotations

import contextvars

subscriber_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "subscriber_id",
    default=None,
)
