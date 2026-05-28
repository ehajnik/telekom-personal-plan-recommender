"""LLM configuration (LiteLLM + Ollama defaults)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

from telekom_profiler.config.app_config import llm_config

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")

OLLAMA_HOST: Final[str] = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")

OLLAMA_ENABLED: Final[bool] = os.getenv("OLLAMA_ENABLED", "true").lower() in (
    "1",
    "true",
    "yes",
)

# Defaults tuned for llama3.2:3b on CPU-only workstations (no dedicated GPU).
OLLAMA_TIMEOUT: Final[float] = float(os.getenv("OLLAMA_TIMEOUT", "180"))
OLLAMA_NUM_PREDICT: Final[int] = int(os.getenv("OLLAMA_NUM_PREDICT", "2048"))

OLLAMA_FALLBACK_ON_ERROR: Final[bool] = os.getenv(
    "OLLAMA_FALLBACK_ON_ERROR", "true"
).lower() in ("1", "true", "yes")

_LLM = llm_config()
_DEFAULT_MODEL = str(_LLM.get("default_model", "ollama/llama3.2:3b"))


def _normalize_model_id(model: str) -> str:
    model_id = model.strip()
    if not model_id:
        return _DEFAULT_MODEL
    if "/" not in model_id:
        return f"ollama/{model_id}"
    return model_id


_MODEL_LIST = [str(item) for item in _LLM.get("models", []) if str(item).strip()]
AVAILABLE_LLM_MODELS: Final[tuple[str, ...]] = tuple(
    _normalize_model_id(item) for item in (_MODEL_LIST or [_DEFAULT_MODEL])
)

OLLAMA_MODEL: Final[str] = _normalize_model_id(os.getenv("OLLAMA_MODEL", _DEFAULT_MODEL))
_selected_model = (
    OLLAMA_MODEL if OLLAMA_MODEL in AVAILABLE_LLM_MODELS else AVAILABLE_LLM_MODELS[0]
)


def llm_enabled() -> bool:
    return OLLAMA_ENABLED


def fallback_on_error() -> bool:
    return OLLAMA_FALLBACK_ON_ERROR


def available_models() -> tuple[str, ...]:
    return AVAILABLE_LLM_MODELS


def selected_model() -> str:
    return _selected_model


def set_selected_model(model: str) -> str:
    global _selected_model
    normalized = _normalize_model_id(model)
    if normalized not in AVAILABLE_LLM_MODELS:
        raise ValueError(
            f"Unsupported model '{model}'. Allowed models: {', '.join(AVAILABLE_LLM_MODELS)}"
        )
    _selected_model = normalized
    return _selected_model
