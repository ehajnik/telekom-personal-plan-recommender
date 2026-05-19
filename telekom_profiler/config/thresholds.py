"""Centralized business thresholds for overlays, profiling, and offers."""

from typing import Final

# --- Overlay detection (domain/archetypes.py) ---

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
UPSELL_DATA_GB: Final[float] = 50.0
UPSELL_VOICE_MIN: Final[float] = 1000.0
UPSELL_SMS: Final[float] = 100.0

# --- Offer tiers (domain/offers.py) ---

OFFER_DATA_XL_GB: Final[float] = 70.0
OFFER_DATA_L_GB: Final[float] = 35.0
OFFER_DATA_M_GB: Final[float] = 15.0
OFFER_DATA_PREPAID_MAX_GB: Final[float] = 8.0
OFFER_VOICE_PREPAID_MAX: Final[float] = 300.0
OFFER_DATA_BOOST_GB: Final[float] = 45.0
OFFER_MULTISIM_DATA_GB: Final[float] = 25.0
OFFER_ROAMING_ADDON_DAYS: Final[float] = 8.0

# --- Archetype-biased offer adjustments ---

ARCHETYPE_ROAMER = "Roamer"
ARCHETYPE_CHATTERBOX = "Chatterbox"
ARCHETYPE_STREAMER = "Streamer"
ARCHETYPE_MESSENGER = "Messenger"
ARCHETYPE_ESSENTIAL = "Essential"
