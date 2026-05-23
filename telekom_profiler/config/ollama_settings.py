"""Ollama local LLM configuration."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")

OLLAMA_HOST: Final[str] = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL: Final[str] = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

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


def llm_enabled() -> bool:
    return OLLAMA_ENABLED


def fallback_on_error() -> bool:
    return OLLAMA_FALLBACK_ON_ERROR
