"""LiteLLM chat client (configured for local Ollama by default)."""

from __future__ import annotations

import logging
import time

from telekom_profiler.config.ollama_settings import (
    LITELLM_API_BASE,
    OLLAMA_HOST,
    OLLAMA_NUM_PREDICT,
    OLLAMA_TIMEOUT,
    llm_enabled,
    model_provider,
    selected_model,
)

_logger = logging.getLogger(__name__)


def reset_client() -> None:
    """No-op shim for compatibility with existing reset hooks."""
    return None


def _is_truncated(finish_reason: object) -> bool:
    reason = str(finish_reason or "").strip().lower()
    return reason in {"length", "max_tokens"}


def _missing_headings(content: str, required_headings: tuple[str, ...]) -> list[str]:
    return [heading for heading in required_headings if heading not in content]


def chat_completion(
    user_prompt: str,
    *,
    temperature: float = 0.3,
    model: str | None = None,
    required_headings: tuple[str, ...] = (),
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
    provider = model_provider(active_model)
    started = time.perf_counter()
    try:
        completion_kwargs: dict[str, object] = {
            "model": active_model,
            "messages": [{"role": "user", "content": user_prompt}],
            "timeout": OLLAMA_TIMEOUT,
            "temperature": temperature,
            "max_tokens": OLLAMA_NUM_PREDICT,
        }
        if provider == "ollama":
            completion_kwargs["api_base"] = OLLAMA_HOST
        elif LITELLM_API_BASE:
            completion_kwargs["api_base"] = LITELLM_API_BASE

        response = completion(**completion_kwargs)
        choice = response.choices[0]
        content = choice.message.content
        finish_reason = getattr(choice, "finish_reason", None)
        if _is_truncated(finish_reason):
            retry_tokens = min(max(int(OLLAMA_NUM_PREDICT * 1.5), OLLAMA_NUM_PREDICT + 512), 4096)
            retry_messages = [
                {
                    "role": "user",
                    "content": (
                        f"{user_prompt}\n\n"
                        "IMPORTANT: Return a complete response with all required sections. "
                        "Do not stop mid-sentence."
                    ),
                }
            ]
            retry_kwargs = dict(completion_kwargs)
            retry_kwargs["messages"] = retry_messages
            retry_kwargs["max_tokens"] = retry_tokens
            response = completion(**retry_kwargs)
            content = response.choices[0].message.content
        if required_headings:
            missing = _missing_headings(str(content or ""), required_headings)
            if missing:
                repair_tokens = min(
                    max(int(OLLAMA_NUM_PREDICT * 1.5), OLLAMA_NUM_PREDICT + 512),
                    4096,
                )
                headings_list = "\n".join(f"- {h}" for h in required_headings)
                repair_messages = [
                    {
                        "role": "user",
                        "content": (
                            f"{user_prompt}\n\n"
                            "IMPORTANT: Your previous answer was incomplete. "
                            "Return a complete response with all required sections "
                            "and headings, in order:\n"
                            f"{headings_list}\n\n"
                            "Do not stop mid-sentence."
                        ),
                    }
                ]
                repair_kwargs = dict(completion_kwargs)
                repair_kwargs["messages"] = repair_messages
                repair_kwargs["max_tokens"] = repair_tokens
                response = completion(**repair_kwargs)
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
        endpoint = (
            OLLAMA_HOST
            if provider == "ollama"
            else (LITELLM_API_BASE or "provider endpoint")
        )
        _logger.warning("LiteLLM connection failed endpoint=%s: %s", endpoint, exc)
        if provider == "ollama":
            raise RuntimeError(
                f"Cannot reach LLM endpoint at {OLLAMA_HOST}. "
                f"Start Ollama (ollama serve) and pull the model ({active_model})."
            ) from exc
        raise RuntimeError(
            f"Cannot reach provider endpoint for model '{active_model}'. "
            "Check internet connectivity and API base settings."
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
            if provider != "ollama":
                raise RuntimeError(
                    f"Cannot reach provider endpoint for model '{active_model}'. "
                    "Check network and credentials."
                ) from exc
            raise RuntimeError(
                f"Cannot reach LLM endpoint at {OLLAMA_HOST}. "
                f"Run: ollama serve  &&  ollama pull {active_model.removeprefix('ollama/')}"
            ) from exc
        if "not found" in err or "404" in err:
            if provider != "ollama":
                raise RuntimeError(
                    f"Model '{active_model}' not found for provider '{provider}'. "
                    "Use a currently supported provider model id and verify API access."
                ) from exc
            raise RuntimeError(
                f"Model '{active_model}' not found. "
                f"Run: ollama pull {active_model.removeprefix('ollama/')}"
            ) from exc
        if "api key" in err or "unauthorized" in err or "authentication" in err or "401" in err:
            key_hint = {
                "openai": "OPENAI_API_KEY",
                "anthropic": "ANTHROPIC_API_KEY",
                "gemini": "GEMINI_API_KEY (or GOOGLE_API_KEY)",
            }.get(provider, "provider API key")
            raise RuntimeError(
                f"Authentication failed for model '{active_model}'. "
                f"Set {key_hint} in your environment."
            ) from exc
        raise RuntimeError(f"LiteLLM request failed: {exc}") from exc
