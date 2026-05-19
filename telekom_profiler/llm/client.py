"""Ollama chat client."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from telekom_profiler.config.ollama_settings import (
    OLLAMA_HOST,
    OLLAMA_MODEL,
    OLLAMA_NUM_PREDICT,
    OLLAMA_TIMEOUT,
    llm_enabled,
)

if TYPE_CHECKING:
    from ollama import Client

_logger = logging.getLogger(__name__)
_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        from ollama import Client

        _client = Client(host=OLLAMA_HOST, timeout=OLLAMA_TIMEOUT)
    return _client


def reset_client() -> None:
    """Drop cached client (tests or host change)."""
    global _client
    _client = None


def chat_completion(user_prompt: str, *, temperature: float = 0.3) -> str:
    """
    Run a single-turn chat completion via local Ollama.

    Raises ``RuntimeError`` if Ollama is disabled, unreachable, or returns empty content.
    """
    if not llm_enabled():
        raise RuntimeError(
            "Ollama is disabled. Set OLLAMA_ENABLED=true in .env or remove the variable."
        )

    try:
        from ollama import Client  # noqa: F401 — verify package present
    except ImportError as exc:
        raise RuntimeError("Install the ollama package: pip install ollama") from exc

    started = time.perf_counter()
    try:
        client = _get_client()
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": user_prompt}],
            options={
                "temperature": temperature,
                "num_predict": OLLAMA_NUM_PREDICT,
            },
        )
        content = response.message.content
        if not content or not str(content).strip():
            raise RuntimeError("Ollama returned an empty response.")
        elapsed_ms = (time.perf_counter() - started) * 1000
        _logger.info(
            "Ollama completion ok model=%s duration_ms=%.0f",
            OLLAMA_MODEL,
            elapsed_ms,
        )
        return str(content).strip()
    except RuntimeError:
        raise
    except ConnectionError as exc:
        _logger.warning("Ollama connection failed host=%s: %s", OLLAMA_HOST, exc)
        raise RuntimeError(
            f"Cannot reach Ollama at {OLLAMA_HOST}. "
            f"Start the server (ollama serve) and pull the model (ollama pull {OLLAMA_MODEL})."
        ) from exc
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000
        _logger.warning(
            "Ollama request failed model=%s duration_ms=%.0f error=%s",
            OLLAMA_MODEL,
            elapsed_ms,
            exc,
        )
        err = str(exc).lower()
        if "connection" in err or "refused" in err:
            raise RuntimeError(
                f"Cannot reach Ollama at {OLLAMA_HOST}. "
                f"Run: ollama serve  &&  ollama pull {OLLAMA_MODEL}"
            ) from exc
        if "not found" in err or "404" in err:
            raise RuntimeError(
                f"Model '{OLLAMA_MODEL}' not found. Run: ollama pull {OLLAMA_MODEL}"
            ) from exc
        raise RuntimeError(f"Ollama request failed: {exc}") from exc
