"""Rule-based B2C plan and add-on recommendations (Telekom Deutschland catalog)."""

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

_ML_LIGHT = "Light / occasional user"
_ML_STREAMING = "Streaming & data-heavy"
_ML_VOICE = "Voice-centric"
_ML_ROAMING = "Roaming / travel-heavy"
_ML_UNDER = "Underutilized / overspending"

_TARIFF_XL = (
    "MagentaMobil XL (MM-XL-001)",
    "€84.95",
    "Unlimited data in Germany; suited to very high usage and streaming.",
)
_TARIFF_L = (
    "MagentaMobil L (MM-L-001)",
    "€59.95",
    "100 GB; includes 5 GB roaming (LG 2/3) and unlimited voice to EU/CH/GB/TR.",
)
_TARIFF_M = (
    "MagentaMobil M (MM-M-001)",
    "€49.95",
    "50 GB; balanced data and flat domestic voice.",
)
_TARIFF_S = (
    "MagentaMobil S (MM-S-001)",
    "€39.95",
    "30 GB; entry postpaid with flat domestic voice/SMS.",
)
_TARIFF_XS = (
    "MagentaMobil XS (MM-XS-001)",
    "€29.95",
    "20 GB; lowest MagentaMobil postpaid tier.",
)
_TARIFF_PREPAID_S = (
    "MagentaMobil Prepaid S (MP-PP-S-001)",
    "€4.95 / 4 weeks",
    "1 GB; very light usage without contract binding.",
)
_TARIFF_PREPAID_M = (
    "MagentaMobil Prepaid M (MP-PP-M-001)",
    "€9.95 / 4 weeks",
    "13 GB; flexible prepaid with data rollover and HotSpot Flat.",
)
_TARIFF_PREPAID_L = (
    "MagentaMobil Prepaid L (MP-PP-L-001)",
    "€14.95 / 4 weeks",
    "25 GB; prepaid alternative for moderate usage.",
)
_TARIFF_PLUS = (
    "MagentaMobil PlusKarte (MM-PLUS-001)",
    "€19.95",
    "Second line sharing the main contract data pool (up to 5×).",
)


def _select_tariff(
    data: dict[str, float],
    scoring: ScoringResult | None,
) -> tuple[str, str, str]:
    """Pick base tariff from usage thresholds, biased by primary archetype when known."""
    primary = scoring.primary_name if scoring else None

    if primary == _ML_LIGHT or (
        primary == ARCHETYPE_ESSENTIAL and data["data_gb"] < OFFER_DATA_M_GB
    ):
        if data["data_gb"] < 3 and data["voice_min"] < OFFER_VOICE_PREPAID_MAX:
            return _TARIFF_PREPAID_S
        if data["data_gb"] < OFFER_DATA_PREPAID_MAX_GB:
            return _TARIFF_PREPAID_M
        return _TARIFF_XS if data["data_gb"] < 15 else _TARIFF_S
    if primary == _ML_STREAMING or primary == ARCHETYPE_STREAMER:
        return _TARIFF_XL if data["data_gb"] >= OFFER_DATA_L_GB else _TARIFF_L
    if primary == _ML_VOICE or primary == ARCHETYPE_CHATTERBOX:
        return _TARIFF_M if data["data_gb"] >= OFFER_DATA_M_GB else _TARIFF_S
    if primary == _ML_ROAMING or primary == ARCHETYPE_ROAMER:
        return _TARIFF_L if data["data_gb"] >= OFFER_DATA_M_GB else _TARIFF_M
    if primary == _ML_UNDER:
        if data["data_gb"] < OFFER_DATA_PREPAID_MAX_GB:
            return _TARIFF_PREPAID_M
        return _TARIFF_XS if data["data_gb"] < OFFER_DATA_M_GB else _TARIFF_S
    if primary == ARCHETYPE_ESSENTIAL and data["data_gb"] < OFFER_DATA_M_GB:
        return _TARIFF_PREPAID_M if data["data_gb"] < OFFER_DATA_PREPAID_MAX_GB else _TARIFF_XS
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
        return _TARIFF_PREPAID_M
    if data["data_gb"] < OFFER_DATA_M_GB:
        return _TARIFF_XS
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
        primary_note = f" Primary profile: **{scoring.primary_name}**."

    addons: list[tuple[str, str, str]] = []
    roaming_threshold = OFFER_ROAMING_ADDON_DAYS
    if scoring and scoring.primary_name == ARCHETYPE_ROAMER:
        roaming_threshold = max(4.0, OFFER_ROAMING_ADDON_DAYS - 2)

    primary_name = scoring.primary_name if scoring else None
    if data["roaming_days"] >= roaming_threshold or primary_name in (
        _ML_ROAMING,
        ARCHETYPE_ROAMER,
    ):
        addons.append(
            (
                "Travel & Surf 4-WeekPass (ADD-TS-4W-001)",
                "from €49.95",
                f"{data['roaming_days']:.0f} roaming days/month — data in roaming LG 2/3 (pass.telekom.de).",
            )
        )
        if data["roaming_days"] >= 12:
            addons.append(
                (
                    "Travel Mobil Basic (ADD-TMB-001)",
                    "€14.95 / booking",
                    "Voice/SMS/data bundle for longer non-EU stays.",
                )
            )
    if data["data_gb"] >= OFFER_DATA_BOOST_GB and tariff[0] != _TARIFF_XL[0]:
        addons.append(
            (
                "MagentaMobil Special (ADD-SPEC-001)",
                "€10.00",
                "10 GB plus 100 GB Datendepot (24 months) for domestic usage peaks.",
            )
        )
    multisim_threshold = OFFER_MULTISIM_DATA_GB
    if data["data_gb"] >= multisim_threshold and "PlusKarte" not in tariff[0]:
        addons.append(
            (
                "MagentaMobil PlusKarte (MM-PLUS-001)",
                "€19.95",
                "Second device on the same data allowance as the main contract.",
            )
        )

    is_prepaid = "Prepaid" in tariff[0]
    channel = (
        "**Prepaid (MagentaMobil Prepaid)** — billed every 4 weeks, no minimum term; "
        "good for variable usage."
        if is_prepaid
        else "**Postpaid (MagentaMobil)** — predictable monthly bill; typically 24-month "
        "term (or **Flex** with no minimum term, SIM-only)."
    )

    addon_rows = "\n".join(
        f"| {name} | {price} | {note} |" for name, price, note in addons
    ) or "| — | — | No add-ons required at this usage level |"

    addon_bullets = (
        "\n".join(f"- **{a[0]}** ({a[1]}): {a[2]}" for a in addons)
        if addons
        else "- No essential add-ons; review usage at contract renewal."
    )

    return f"""### 1. Recommended main tariff
<mark>{tariff[0]}</mark> — {tariff[2]}{primary_note}

### 2. Recommended add-ons and options
{addon_bullets}

### 3. Contract and channel notes
{channel}
- **MeinMagenta app** / shop: tariff changes and Travel & Surf booking.
- **MagentaMobil Young** (18–27): check eligibility for lower price and extra data.
- **MagentaEINS**: bundle discount with MagentaZuhause when eligible in CRM.

### 4. Indicative pricing
| Product | Monthly price (brutto) | Notes |
|---------|------------------------|-------|
| {tariff[0]} | {tariff[1]} | Main tariff |
{addon_rows}

*Catalog based on Telekom price lists (`plans_and_options.md`). Verify in BSS/PCM before quoting.*

### 5. Important caveats
- **EU roaming:** fair-use applies on unlimited tiers; Young XL includes a 200 GB EU allowance.
- After included data is used: **throttling to 64/16 kbit/s** (postpaid/prepaid).
- **Travel & Surf:** prices and volumes vary by country — book at pass.telekom.de before travel.
- Switzerland/GB: roaming LG 1 with fair-use limits on voice/SMS.

### 6. Next steps for the agent
- Check current contract and remaining term in CRM (binding, device instalments).
- If roaming ≥ {OFFER_ROAMING_ADDON_DAYS:.0f} days: confirm destinations (EU vs LG 2/3) and recommend a T&S pass.
- Offer tariff change or PlusKarte via MeinMagenta when eligible.
"""
