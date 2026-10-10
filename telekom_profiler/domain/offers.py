"""Rule-based B2C plan and add-on recommendations (Telekom Deutschland catalog).

Sizing rule: recommend the **cheapest tariff whose data allowance covers the
projected need**, where

    need = current GB × (1 + positive annual data trend) × OFFER_DATA_HEADROOM

The primary profile decides the channel (prepaid vs postpaid) and minimum tier
(e.g. travel-heavy → at least MagentaMobil L for the larger non-EU volume). The
catalogue lives in ``domain/catalog.py``; this module never hard-codes prices.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from telekom_profiler.config.thresholds import (
    ARCHETYPE_CHATTERBOX,
    ARCHETYPE_ESSENTIAL,
    ARCHETYPE_MESSENGER,
    ARCHETYPE_ROAMER,
    ARCHETYPE_STREAMER,
    OFFER_DATA_HEADROOM,
    OFFER_LONG_STAY_ROAMING_DAYS,
    OFFER_ROAMING_ADDON_DAYS,
)
from telekom_profiler.domain.catalog import (
    CATALOG_STAND,
    MAGENTA_EINS,
    PLUSKARTE,
    PLUSKARTE_DATA,
    POSTPAID,
    PREPAID,
    PREPAID_S_VOICE_MAX_MIN,
    TS_2DAY,
    TS_4WEEK_LG2,
    WELCOME_PASS,
    AddOn,
    Tariff,
    cheapest_covering,
    tariff_by_sku,
)
from telekom_profiler.domain.models import ScoringResult

Intent = Literal["light", "streaming", "voice", "roaming", "broad", "unknown"]

# ML labels and legacy archetype names map onto one set of sales intents.
_INTENT_BY_PROFILE: dict[str, Intent] = {
    "Light / occasional user": "light",
    "Streaming & data-heavy": "streaming",
    "Voice-centric": "voice",
    "Roaming / travel-heavy": "roaming",
    "Broad usage profile": "broad",
    ARCHETYPE_ESSENTIAL: "light",
    ARCHETYPE_STREAMER: "streaming",
    ARCHETYPE_CHATTERBOX: "voice",
    ARCHETYPE_ROAMER: "roaming",
    ARCHETYPE_MESSENGER: "broad",
}

_MIN_TRAVEL_TARIFF = "MM-L-001"


@dataclass(frozen=True, slots=True)
class OfferRecommendation:
    """Structured result of the rule-based offer engine."""

    tariff: Tariff
    alternative: Tariff | None
    data_need_gb: float
    intent: Intent
    reasons: tuple[str, ...]
    addons: tuple[AddOn, ...]
    addon_reasons: tuple[str, ...]
    travel_relevant: bool


def projected_data_need(data_gb: float, data_trend_pct: float) -> float:
    """Monthly GB to cover in 12 months: growth is added, decline is ignored (safety)."""
    growth = max(0.0, data_trend_pct) / 100.0
    return data_gb * (1.0 + growth) * OFFER_DATA_HEADROOM


def profile_intent(primary: str | None) -> Intent:
    return _INTENT_BY_PROFILE.get(primary or "", "unknown")


def _fits_prepaid(data: Mapping[str, float], need: float) -> bool:
    largest_prepaid = max(t.data_gb or 0.0 for t in PREPAID if t.data_gb is not None)
    return need <= largest_prepaid and data["roaming_days"] < OFFER_ROAMING_ADDON_DAYS


def _cheapest_prepaid(data: Mapping[str, float], need: float) -> Tariff:
    candidates = PREPAID
    if data["voice_min"] > PREPAID_S_VOICE_MAX_MIN:
        candidates = tuple(t for t in PREPAID if t.sku != "MP-PP-S-001")
    return cheapest_covering(candidates, need)


def recommend(
    data: Mapping[str, float],
    scoring: ScoringResult | None = None,
) -> OfferRecommendation:
    """Select tariff, alternative and add-ons for one usage snapshot."""
    primary = scoring.primary_name if scoring else None
    intent = profile_intent(primary)
    need = projected_data_need(float(data["data_gb"]), float(data["data_trend"]))
    roaming_days = float(data["roaming_days"])
    travel = roaming_days >= OFFER_ROAMING_ADDON_DAYS or intent == "roaming"

    reasons = [
        f"Data need: {data['data_gb']:.0f} GB × (1 + {max(0.0, data['data_trend']):.0f} % "
        f"growth) × {OFFER_DATA_HEADROOM:.2f} headroom ≈ **{need:.0f} GB / month**."
    ]

    prepaid_fit = _fits_prepaid(data, need)
    postpaid = cheapest_covering(POSTPAID, need)
    if travel and (postpaid.data_gb is not None and postpaid.data_gb < 100):
        postpaid = tariff_by_sku(_MIN_TRAVEL_TARIFF)
        reasons.append(
            f"Frequent travel ({roaming_days:.0f} days/month): at least MagentaMobil L for "
            f"{postpaid.lg23_data_gb_per_year:g} GB/year non-EU data and calls to EU/CH/GB/TR."
        )

    if intent == "light" and prepaid_fit:
        tariff = _cheapest_prepaid(data, need)
        alternative: Tariff | None = postpaid
        reasons.append(
            "Light usage profile: prepaid avoids a 24-month term and fits the volume."
        )
    else:
        tariff = postpaid
        alternative = _cheapest_prepaid(data, need) if prepaid_fit else None
        if intent == "voice":
            reasons.append(
                "Voice-centric: every MagentaMobil tier includes a German voice flat, "
                "so the tier is sized by data."
            )

    if tariff.data_gb is not None:
        reasons.append(f"{tariff.name} includes {tariff.data_label} — covers the need.")
    else:
        reasons.append(f"{tariff.name} has unlimited domestic data.")

    addons: list[AddOn] = []
    addon_reasons: list[str] = []
    if travel:
        if roaming_days >= OFFER_LONG_STAY_ROAMING_DAYS:
            addons.append(TS_4WEEK_LG2)
            addon_reasons.append(
                f"{roaming_days:.0f} roaming days/month — only for long non-EU stays beyond "
                "the tariff's annual LG 2/3 volume."
            )
        else:
            addons.append(TS_2DAY)
            addon_reasons.append(
                f"{roaming_days:.0f} roaming days/month — short non-EU trips beyond the "
                "annual LG 2/3 volume; EU trips need no pass."
            )
        if tariff.family == "postpaid":
            addons.append(WELCOME_PASS)
            addon_reasons.append("Free 1 GB on arrival outside the EU (twice per year).")

    return OfferRecommendation(
        tariff=tariff,
        alternative=alternative,
        data_need_gb=need,
        intent=intent,
        reasons=tuple(reasons),
        addons=tuple(addons),
        addon_reasons=tuple(addon_reasons),
        travel_relevant=travel,
    )


def render_offer_report(
    _profile_text: str,
    data: Mapping[str, float],
    *,
    scoring: ScoringResult | None = None,
) -> str:
    """Build offer markdown aligned with ``prompts/templates/run_offer.md``."""
    rec = recommend(data, scoring)
    tariff = rec.tariff
    primary_note = f" Primary profile: **{scoring.primary_name}**." if scoring else ""

    reason_bullets = "\n".join(f"- {r}" for r in rec.reasons)
    alternative_line = ""
    if rec.alternative is not None:
        alt = rec.alternative
        alternative_line = (
            f"\n\n**Alternative:** {alt.display} — {alt.data_label}, {alt.price_label}"
            + (
                " (no contract term; no annual non-EU volume, no PlusKarten)."
                if alt.family == "prepaid"
                else " (contract with annual non-EU volume and PlusKarte option)."
            )
        )

    addon_bullets = (
        "\n".join(
            f"- **{a.display}** ({a.price_label}): {reason}"
            for a, reason in zip(rec.addons, rec.addon_reasons, strict=True)
        )
        if rec.addons
        else "- No add-ons required at this usage level."
    )

    if tariff.family == "prepaid":
        channel = (
            "**Prepaid (MagentaMobil Prepaid)** — billed every 4 weeks, no minimum term; "
            "unused data rolls over (M and above)."
        )
    else:
        channel = (
            "**Postpaid (MagentaMobil)** — predictable monthly bill; 24-month term or "
            "**Flex** (no minimum term, SIM-only)."
        )
        if tariff.multisim_included:
            channel += f" Includes {tariff.multisim_included} MultiSIM card(s)."

    period_note = "per 4 weeks" if tariff.family == "prepaid" else "monthly"
    addon_rows = "\n".join(f"| {a.display} | {a.price_label} | Option |" for a in rec.addons)
    pricing_rows = f"| {tariff.display} | {tariff.price_label} | Main tariff ({period_note}) |"
    if addon_rows:
        pricing_rows += "\n" + addon_rows

    travel_caveat = ""
    if tariff.family == "postpaid":
        travel_caveat = (
            f"- **Non-EU roaming:** {tariff.name} includes {tariff.lg23_data_gb_per_year:g} GB "
            "per calendar year in LG 2/3; Travel & Surf passes only beyond that."
        )
    else:
        travel_caveat = (
            "- **Non-EU roaming:** prepaid has no annual LG 2/3 volume — book Travel & Surf "
            "passes before travelling outside the EU."
        )

    next_steps = [
        "- Check current contract, remaining term and device instalments in CRM.",
        f"- Ask about additional devices or family members → **{PLUSKARTE.display}** "
        f"({PLUSKARTE.price_label}) or **{PLUSKARTE_DATA.display}** for a tablet.",
        f"- Check **{MAGENTA_EINS.name}** eligibility (fixed line / TV at home) and age "
        "18–27 for **MagentaMobil Young**.",
    ]
    if rec.travel_relevant:
        next_steps.insert(
            1,
            "- Confirm travel destinations (EU / LG 1 vs LG 2/3) before booking passes.",
        )

    return f"""### 1. Recommended main tariff
<mark>{tariff.display}</mark> — {tariff.data_label}, <mark>{tariff.price_label}</mark>.{primary_note}

{reason_bullets}{alternative_line}

### 2. Recommended add-ons and options
{addon_bullets}

### 3. Contract and channel notes
{channel}
- **MeinMagenta app** / shop: tariff changes and Travel & Surf booking.

### 4. Indicative pricing
| Product | Price (brutto) | Notes |
|---------|----------------|-------|
{pricing_rows}

*Catalog Stand {CATALOG_STAND} (`plans_and_options.md`). Verify in BSS/PCM before quoting.*

### 5. Important caveats
- **EU roaming (LG 1, incl. CH/GB):** domestic allowance applies; fair use on unlimited tiers.
{travel_caveat}
- After the included volume, speed is throttled.
- Sizing assumes the usage snapshot is representative; re-check after big life changes.

### 6. Next steps for the agent
{chr(10).join(next_steps)}
"""
