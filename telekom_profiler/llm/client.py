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

_NO_SAMPLING_PROVIDERS = frozenset({"anthropic"})


def reset_client() -> None:
    """No-op shim for compatibility with existing reset hooks."""
    return None


def _is_truncated(finish_reason: object) -> bool:
    reason = str(finish_reason or "").strip().lower()
    return reason in {"length", "max_tokens"}


def _retry_token_budget() -> int:
    """Completion budget for repair retries: always larger than the first attempt."""
    return int(OLLAMA_NUM_PREDICT * 1.5)


def _missing_headings(content: str, required_headings: tuple[str, ...]) -> list[str]:
    return [heading for heading in required_headings if heading not in content]


def _looks_like_prompt_echo(content: str) -> bool:
    text = content.lower()
    return (
        "## your task" in text
        and "## input:" in text
        or "{customer_profile}" in text
        or "{tariffs_and_options}" in text
        or "{slider_features}" in text
    )


def chat_completion(
    user_prompt: str,
    *,
    temperature: float = 0.3,
    model: str | None = None,
    required_headings: tuple[str, ...] = (),
    required_tail: str = "",
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
            "max_tokens": OLLAMA_NUM_PREDICT,
        }
        # Current Claude models reject sampling parameters (HTTP 400); others accept them.
        if provider not in _NO_SAMPLING_PROVIDERS:
            completion_kwargs["temperature"] = temperature
        if provider == "ollama":
            completion_kwargs["api_base"] = OLLAMA_HOST
        elif LITELLM_API_BASE:
            completion_kwargs["api_base"] = LITELLM_API_BASE

        def _retry(instruction: str) -> object:
            """Re-ask with an explicit instruction and a larger completion budget."""
            retry_kwargs = dict(completion_kwargs)
            retry_kwargs["messages"] = [
                {"role": "user", "content": f"{user_prompt}\n\nIMPORTANT: {instruction}"}
            ]
            retry_kwargs["max_tokens"] = _retry_token_budget()
            return completion(**retry_kwargs).choices[0].message.content

        response = completion(**completion_kwargs)
        choice = response.choices[0]
        content = choice.message.content
        if _is_truncated(getattr(choice, "finish_reason", None)):
            content = _retry(
                "Return a complete response with all required sections. "
                "Do not stop mid-sentence."
            )
        if required_headings:
            missing = _missing_headings(str(content or ""), required_headings)
            if missing:
                headings_list = "\n".join(f"- {h}" for h in required_headings)
                content = _retry(
                    "Your previous answer was incomplete. Return a complete response with "
                    f"all required sections and headings, in order:\n{headings_list}\n\n"
                    "Do not stop mid-sentence."
                )
        if required_tail and not str(content or "").rstrip().endswith(required_tail):
            content = _retry(
                "Your previous answer was cut off. "
                f"Regenerate the full answer and end exactly with `{required_tail}`."
            )
        if _looks_like_prompt_echo(str(content or "")):
            content = _retry(
                "Do not repeat or quote the prompt/template. "
                "Return only the final completed report content."
            )
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
