"""Ollama chat client."""

from __future__ import annotations

from telekom_profiler.config.ollama_settings import OLLAMA_HOST, OLLAMA_MODEL, llm_enabled


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
        from ollama import Client
    except ImportError as exc:
        raise RuntimeError("Install the ollama package: pip install ollama") from exc

    try:
        client = Client(host=OLLAMA_HOST)
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": user_prompt}],
            options={"temperature": temperature},
        )
        content = response.message.content
        if not content or not str(content).strip():
            raise RuntimeError("Ollama returned an empty response.")
        return str(content).strip()
    except RuntimeError:
        raise
    except ConnectionError as exc:
        raise RuntimeError(
            f"Cannot reach Ollama at {OLLAMA_HOST}. "
            f"Start the server (ollama serve) and pull the model (ollama pull {OLLAMA_MODEL})."
        ) from exc
    except Exception as exc:
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
