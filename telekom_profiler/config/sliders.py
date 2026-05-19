"""Slider definitions, profile presets, and UI placeholder messages."""

from __future__ import annotations

import json
from typing import Final

from telekom_profiler.paths import ARTIFACTS_DIR

CUSTOM_PROFILE: Final[str] = "— Custom —"
PLACEHOLDER_PREFIX: Final[str] = "_"

MSG_RUN_PROFILE: Final[str] = "_Profile analysis appears here._"
MSG_AFTER_PROFILE: Final[str] = "_Use **Generate offer** when ready._"
MSG_RUN_PROFILE_FIRST: Final[str] = "_Complete profiling before generating an offer._"
MSG_GENERATE_OFFER: Final[str] = "_Tariff recommendation appears here._"

SliderSpec = tuple[str, int, int, int]

USAGE_SLIDERS: Final[dict[str, SliderSpec]] = {
    "data_gb": ("Monthly data (GB)", 0, 150, 30),
    "voice_min": ("Voice minutes", 0, 3000, 400),
    "sms_count": ("SMS count", 0, 500, 50),
    "roaming_days": ("Roaming days / month", 0, 30, 2),
}

TREND_SLIDERS: Final[dict[str, SliderSpec]] = {
    "data_trend": ("Data trend", -50, 50, 5),
    "voice_trend": ("Voice trend", -50, 50, 0),
}

SLIDER_KEYS: Final[tuple[str, ...]] = tuple(USAGE_SLIDERS) + tuple(TREND_SLIDERS)

ProfilePreset = dict[str, int] | None

PROFILES: Final[dict[str, ProfilePreset]] = {
    CUSTOM_PROFILE: None,
    "Streamer": {
        "data_gb": 100,
        "voice_min": 150,
        "sms_count": 20,
        "roaming_days": 3,
        "data_trend": 12,
        "voice_trend": -5,
    },
    "Chatterbox": {
        "data_gb": 12,
        "voice_min": 2000,
        "sms_count": 80,
        "roaming_days": 2,
        "data_trend": -5,
        "voice_trend": 8,
    },
    "Essential": {
        "data_gb": 8,
        "voice_min": 200,
        "sms_count": 30,
        "roaming_days": 1,
        "data_trend": 0,
        "voice_trend": 0,
    },
    "Roamer": {
        "data_gb": 35,
        "voice_min": 400,
        "sms_count": 25,
        "roaming_days": 15,
        "data_trend": 5,
        "voice_trend": 0,
    },
    "Messenger": {
        "data_gb": 25,
        "voice_min": 100,
        "sms_count": 200,
        "roaming_days": 1,
        "data_trend": 3,
        "voice_trend": -8,
    },
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
