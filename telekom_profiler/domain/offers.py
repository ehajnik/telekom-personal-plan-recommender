"""Rule-based B2C plan and add-on recommendations."""

from __future__ import annotations

from telekom_profiler.config.thresholds import (
    ARCHETYPE_CHATTERBOX,
    ARCHETYPE_ESSENTIAL,
    ARCHETYPE_MESSENGER,
    ARCHETYPE_ROAMER,
    ARCHETYPE_STREAMER,
    OFFER_DATA_BOOST_GB,
    OFFER_DATA_L_GB,
    OFFER_DATA_M_GB,
    OFFER_DATA_PREPAID_MAX_GB,
    OFFER_DATA_XL_GB,
    OFFER_MULTISIM_DATA_GB,
    OFFER_ROAMING_ADDON_DAYS,
    OFFER_VOICE_PREPAID_MAX,
)
from telekom_profiler.domain.models import ScoringResult

_TARIFF_XL = ("MagentaMobil XL", "€69.95", "Unlimited DE data; fits heavy streaming.")
_TARIFF_L = ("MagentaMobil L", "€59.95", "50 GB matches sustained high data use.")
_TARIFF_M = ("MagentaMobil M", "€49.95", "Balanced data and flat voice.")
_TARIFF_S = ("MagentaMobil S", "€39.95", "Entry postpaid for light-medium use.")
_TARIFF_PREPAID = (
    "MagentaMobil Prepaid M",
    "€14.95",
    "Low usage suits flexible prepaid.",
)


def _select_tariff(
    data: dict[str, float],
    scoring: ScoringResult | None,
) -> tuple[str, str, str]:
    """Pick base tariff from usage thresholds, biased by primary archetype when known."""
    primary = scoring.primary_name if scoring else None

    if primary == ARCHETYPE_ESSENTIAL and data["data_gb"] < OFFER_DATA_M_GB:
        return _TARIFF_PREPAID
    if primary == ARCHETYPE_CHATTERBOX and data["data_gb"] < OFFER_DATA_L_GB:
        return _TARIFF_M
    if primary == ARCHETYPE_STREAMER or data["data_gb"] >= OFFER_DATA_XL_GB:
        return _TARIFF_XL
    if primary == ARCHETYPE_ROAMER and data["data_gb"] >= OFFER_DATA_M_GB:
        return _TARIFF_L
    if primary == ARCHETYPE_MESSENGER and OFFER_DATA_M_GB <= data["data_gb"] < OFFER_DATA_L_GB:
        return _TARIFF_M

    if data["data_gb"] >= OFFER_DATA_XL_GB:
        return _TARIFF_XL
    if data["data_gb"] >= OFFER_DATA_L_GB:
        return _TARIFF_L
    if data["data_gb"] >= OFFER_DATA_M_GB:
        return _TARIFF_M
    if data["data_gb"] < OFFER_DATA_PREPAID_MAX_GB and data["voice_min"] < OFFER_VOICE_PREPAID_MAX:
        return _TARIFF_PREPAID
    return _TARIFF_S


def render_offer_report(
    _profile_text: str,
    data: dict[str, float],
    *,
    scoring: ScoringResult | None = None,
) -> str:
    """Build offer markdown aligned with ``prompts/templates/run_offer.md``."""
    tariff = _select_tariff(data, scoring)
    primary_note = ""
    if scoring:
        primary_note = f" Primary archetype: **{scoring.primary_name}**."

    addons: list[tuple[str, str, str]] = []
    roaming_threshold = OFFER_ROAMING_ADDON_DAYS
    if scoring and scoring.primary_name == ARCHETYPE_ROAMER:
        roaming_threshold = max(4.0, OFFER_ROAMING_ADDON_DAYS - 2)

    if data["roaming_days"] >= roaming_threshold:
        addons.append(
            (
                "EU Roaming Plus",
                "€5.95",
                f"{data['roaming_days']:.0f} roaming days/month — extra EU data pool.",
            )
        )
    if data["data_gb"] >= OFFER_DATA_BOOST_GB and tariff[0] != _TARIFF_XL[0]:
        addons.append(("Data Boost 5 GB", "€4.95", "Safety buffer if between tiers."))
    if data["data_gb"] >= OFFER_MULTISIM_DATA_GB:
        addons.append(("MultiSIM Tablet", "€4.95", "Second device on shared allowance."))
    if scoring and scoring.primary_name == ARCHETYPE_CHATTERBOX:
        addons.append(
            (
                "Flat Voice Comfort",
                "€2.95",
                "Unlimited domestic voice aligned with Chatterbox usage.",
            )
        )

    channel = (
        "**Postpaid (MagentaMobil)** — predictable bill, flat rates."
        if "Prepaid" not in tariff[0]
        else "**Prepaid** — flexibility, no long binding; top up as needed."
    )

    addon_rows = "\n".join(
        f"| {name} | {price} | {note} |" for name, price, note in addons
    ) or "| — | — | No add-ons required at this usage level |"

    addon_bullets = (
        "\n".join(f"- **{a[0]}** ({a[1]}): {a[2]}" for a in addons)
        if addons
        else "- None essential; monitor usage at renewal."
    )

    return f"""### 1. Recommended main tariff
**{tariff[0]}** — {tariff[2]}{primary_note}

### 2. Recommended add-ons and options
{addon_bullets}

### 3. Contract and channel notes
{channel}

### 4. Indicative pricing
| Product | Monthly price (brutto) | Notes |
|---------|------------------------|-------|
| {tariff[0]} | {tariff[1]} | Base plan |
{addon_rows}

*Prototype catalog — verify in BSS before customer quote.*

### 5. Important caveats
- EU roaming subject to fair-use policy on unlimited tiers.
- Intro offers and MagentaEINS discounts require eligibility check in CRM.
- Trends are indicative; confirm last 3 billing months before downgrade/upgrade.

### 6. Next steps for the agent
- Compare recommended tier with current contract in CRM.
- If roaming days ≥ {OFFER_ROAMING_ADDON_DAYS:.0f}, confirm travel countries for EU vs world pack.
- Offer self-service tariff change in MeinMagenta app where eligible.
"""
