"""Centralized business thresholds for overlays, profiling, and offers."""

from typing import Final

# --- Overlay detection (domain/archetypes.py) ---
# Trend thresholds are in % change per year (same unit as the UI trend sliders).

DATA_TREND_GROWTH_MIN: Final[float] = 10.0
VOICE_TREND_DECLINE_MAX: Final[float] = -10.0
ROAMING_HEAVY_DAYS_MIN: Final[float] = 8.0
BUDGET_DATA_GB_MAX: Final[float] = 12.0
BUDGET_VOICE_MIN_MAX: Final[float] = 300.0
BUDGET_ROAMING_DAYS_MAX: Final[float] = 2.0

# --- Confidence scoring (domain/archetypes.py) ---

CONFIDENCE_HIGH_RATIO_MIN: Final[float] = 0.3
CONFIDENCE_MEDIUM_RATIO_MIN: Final[float] = 0.15

# --- Profile narrative (domain/profiling.py) ---

SECONDARY_BLEND_SCORE_FACTOR: Final[float] = 1.3
NARRATIVE_HEAVY_DATA_GB: Final[float] = 60.0
NARRATIVE_HIGH_VOICE_MIN: Final[float] = 800.0
NARRATIVE_HIGH_SMS: Final[float] = 100.0
NARRATIVE_ROAMING_DAYS: Final[float] = 8.0
PAIN_DATA_GB: Final[float] = 40.0
PAIN_LOW_VOICE_MIN: Final[float] = 200.0
UPSELL_VOICE_MIN: Final[float] = 1000.0
UPSELL_SMS: Final[float] = 100.0

# --- Offer sizing (domain/offers.py) ---

# Safety margin on top of the projected monthly data need (10 %).
OFFER_DATA_HEADROOM: Final[float] = 1.10
# Roaming days per month from which travel options are recommended.
OFFER_ROAMING_ADDON_DAYS: Final[float] = 8.0
# Roaming days per month from which a 4-week pass is suggested instead of day passes.
OFFER_LONG_STAY_ROAMING_DAYS: Final[float] = 14.0

# --- Legacy archetype names (rules mode) ---

ARCHETYPE_ROAMER = "Roamer"
ARCHETYPE_CHATTERBOX = "Chatterbox"
ARCHETYPE_STREAMER = "Streamer"
ARCHETYPE_MESSENGER = "Messenger"
ARCHETYPE_ESSENTIAL = "Essential"
