"""LiteLLM chat client (configured for local Ollama by default)."""

from __future__ import annotations

import logging
import time

from telekom_profiler.config.ollama_settings import (
    OLLAMA_HOST,
    OLLAMA_NUM_PREDICT,
    OLLAMA_TIMEOUT,
    llm_enabled,
    selected_model,
)

_logger = logging.getLogger(__name__)


def reset_client() -> None:
    """No-op shim for compatibility with existing reset hooks."""
    return None


def chat_completion(
    user_prompt: str, *, temperature: float = 0.3, model: str | None = None
) -> str:
    """
    Run a single-turn chat completion via LiteLLM.

    Raises ``RuntimeError`` if LLM is disabled, unreachable, or returns empty content.
    """
    if not llm_enabled():
        raise RuntimeError(
            "LLM is disabled. Set OLLAMA_ENABLED=true in .env or remove the variable."
        )

    try:
        from litellm import completion
    except ImportError as exc:
        raise RuntimeError("Install LiteLLM: pip install litellm") from exc

    active_model = model or selected_model()
    started = time.perf_counter()
    try:
        response = completion(
            model=active_model,
            messages=[{"role": "user", "content": user_prompt}],
            api_base=OLLAMA_HOST,
            timeout=OLLAMA_TIMEOUT,
            temperature=temperature,
            max_tokens=OLLAMA_NUM_PREDICT,
        )
        content = response.choices[0].message.content
        if not content or not str(content).strip():
            raise RuntimeError("LLM returned an empty response.")
        elapsed_ms = (time.perf_counter() - started) * 1000
        _logger.info(
            "LiteLLM completion ok model=%s duration_ms=%.0f",
            active_model,
            elapsed_ms,
        )
        return str(content).strip()
    except RuntimeError:
        raise
    except ConnectionError as exc:
        _logger.warning("LiteLLM connection failed host=%s: %s", OLLAMA_HOST, exc)
        raise RuntimeError(
            f"Cannot reach LLM endpoint at {OLLAMA_HOST}. "
            f"Start Ollama (ollama serve) and pull the model ({active_model})."
        ) from exc
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000
        _logger.warning(
            "LiteLLM request failed model=%s duration_ms=%.0f error=%s",
            active_model,
            elapsed_ms,
            exc,
        )
        err = str(exc).lower()
        if "connection" in err or "refused" in err:
            raise RuntimeError(
                f"Cannot reach LLM endpoint at {OLLAMA_HOST}. "
                f"Run: ollama serve  &&  ollama pull {active_model.removeprefix('ollama/')}"
            ) from exc
        if "not found" in err or "404" in err:
            raise RuntimeError(
                f"Model '{active_model}' not found. "
                f"Run: ollama pull {active_model.removeprefix('ollama/')}"
            ) from exc
        raise RuntimeError(f"LiteLLM request failed: {exc}") from exc
