"""Root YAML configuration loader for profiler and ML pipeline."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from telekom_profiler.paths import REPO_ROOT

APP_CONFIG_PATH = REPO_ROOT / "app_config.yaml"


@lru_cache(maxsize=1)
def load_app_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or APP_CONFIG_PATH
    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping at root of {config_path}")
    return data


def model_config() -> dict[str, Any]:
    return dict(load_app_config().get("model", {}))


def runtime_config() -> dict[str, Any]:
    return dict(load_app_config().get("runtime", {}))


def training_config() -> dict[str, Any]:
    return dict(load_app_config().get("training", {}))


def llm_config() -> dict[str, Any]:
    return dict(load_app_config().get("llm", {}))


def ui_config() -> dict[str, Any]:
    return dict(load_app_config().get("ui", {}))

