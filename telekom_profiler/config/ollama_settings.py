"""Ollama local LLM configuration."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")

OLLAMA_HOST: Final[str] = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL: Final[str] = os.getenv("OLLAMA_MODEL", "llama3.2")

# Set OLLAMA_ENABLED=false to use rule-based fallback without calling Ollama.
OLLAMA_ENABLED: Final[bool] = os.getenv("OLLAMA_ENABLED", "true").lower() in (
    "1",
    "true",
    "yes",
)


def llm_enabled() -> bool:
    return OLLAMA_ENABLED
