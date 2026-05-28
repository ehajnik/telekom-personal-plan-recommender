"""Slider definitions, profile presets, and UI placeholder messages."""

from __future__ import annotations

import json
from typing import Final

from telekom_profiler.config.app_config import ui_config
from telekom_profiler.paths import ARTIFACTS_DIR

CUSTOM_PROFILE: Final[str] = "— Custom —"
PLACEHOLDER_PREFIX: Final[str] = "_"

MSG_RUN_PROFILE: Final[str] = "_Profile analysis appears here._"
MSG_AFTER_PROFILE: Final[str] = "_Use **Generate offer** when ready._"
MSG_RUN_PROFILE_FIRST: Final[str] = "_Complete profiling before generating an offer._"
MSG_GENERATE_OFFER: Final[str] = "_Tariff recommendation appears here._"

SliderSpec = tuple[str, int, int, int]

_UI = ui_config()


def _slider_specs(section: str) -> dict[str, SliderSpec]:
    specs = _UI.get(section, {})
    return {k: (str(v[0]), int(v[1]), int(v[2]), int(v[3])) for k, v in specs.items()}


USAGE_SLIDERS: Final[dict[str, SliderSpec]] = _slider_specs("usage_sliders")
TREND_SLIDERS: Final[dict[str, SliderSpec]] = _slider_specs("trend_sliders")

SLIDER_KEYS: Final[tuple[str, ...]] = tuple(USAGE_SLIDERS) + tuple(TREND_SLIDERS)

ProfilePreset = dict[str, int] | None

PROFILES: Final[dict[str, ProfilePreset]] = {
    CUSTOM_PROFILE: None,
    **{k: {kk: int(vv) for kk, vv in v.items()} for k, v in _UI.get("profiles", {}).items()},
}


def profile_template_choices() -> list[str]:
    """Dropdown choices: custom plus ML profile labels when artifacts exist."""
    path = ARTIFACTS_DIR / "profile_characteristics.json"
    if path.is_file():
        try:
            from telekom_profiler.ml.profile_characteristics import load_profiles_document

            doc = load_profiles_document(json.loads(path.read_text(encoding="utf-8")))
            labels = sorted(doc.get("profiles", {}).keys())
            return [CUSTOM_PROFILE, *labels]
        except (json.JSONDecodeError, OSError):
            pass
    return [CUSTOM_PROFILE, *[k for k in PROFILES if k != CUSTOM_PROFILE]]
