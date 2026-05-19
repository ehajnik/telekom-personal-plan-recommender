"""Slider definitions, profile presets, and UI placeholder messages."""

from typing import Final

CUSTOM_PROFILE: Final[str] = "— Custom —"
PLACEHOLDER_PREFIX: Final[str] = "_"

MSG_RUN_PROFILE: Final[str] = "_Run the profile to see analysis here._"
MSG_AFTER_PROFILE: Final[str] = "_Click **Generate offer** after running the profile._"
MSG_RUN_PROFILE_FIRST: Final[str] = "_Run the profile first, then generate an offer._"
MSG_GENERATE_OFFER: Final[str] = "_Generate an offer after profiling._"

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
    "Heavy data user": {
        "data_gb": 95,
        "voice_min": 200,
        "sms_count": 30,
        "roaming_days": 8,
        "data_trend": 15,
        "voice_trend": -5,
    },
    "Chatterbox": {
        "data_gb": 10,
        "voice_min": 2200,
        "sms_count": 120,
        "roaming_days": 5,
        "data_trend": -5,
        "voice_trend": 10,
    },
}
