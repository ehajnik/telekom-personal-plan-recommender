"""Rule-based B2C customer profile generation (legacy archetypes and ML profiles)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from telekom_profiler.config.thresholds import (
    DATA_TREND_GROWTH_MIN,
    NARRATIVE_HEAVY_DATA_GB,
    NARRATIVE_HIGH_SMS,
    NARRATIVE_HIGH_VOICE_MIN,
    NARRATIVE_ROAMING_DAYS,
    PAIN_DATA_GB,
    PAIN_LOW_VOICE_MIN,
    SECONDARY_BLEND_SCORE_FACTOR,
    UPSELL_SMS,
    UPSELL_VOICE_MIN,
    VOICE_TREND_DECLINE_MAX,
)
from telekom_profiler.domain.archetypes import (
    compute_archetype_distances,
    compute_overlays,
    confidence_label,
)
from telekom_profiler.domain.catalog import MAGENTA_EINS, PLUSKARTE
from telekom_profiler.domain.models import ScoringResult
from telekom_profiler.domain.offers import recommend

_ARCHETYPE_CONTEXT: dict[str, str] = {
    "Streamer": "Young professional or household streaming on mobile.",
    "Chatterbox": "Voice-first user, possibly older demographic or tradesperson.",
    "Essential": "Price-conscious user with basic smartphone needs.",
    "Roamer": "Cross-border commuter or frequent leisure traveller.",
    "Messenger": "Messaging-centric, social and chat app usage.",
}

_ML_PROFILE_CONTEXT: dict[str, str] = {
    "Light / occasional user": "Low-intensity mobile user; prepaid or entry postpaid fit.",
    "Streaming & data-heavy": "High data volume; large or unlimited allowance needed.",
    "Voice-centric": "Voice-first; moderate data; German voice flat is essential.",
    "Roaming / travel-heavy": "Frequent international travel; non-EU data allowance matters.",
    "Broad usage profile": "Above-average data, voice and SMS without one dominant dimension.",
}


def usage_pains_and_upsells(
    data: Mapping[str, float],
    scoring: ScoringResult | None = None,
) -> tuple[list[str], list[str]]:
    """Pain points and upsell signals from concrete usage (shared by all report types).

    Product references come from the catalogue via the offer engine, so the profile
    never mentions a product that the offer step cannot recommend.
    """
    rec = recommend(data, scoring)
    pains: list[str] = []
    if data["data_gb"] > PAIN_DATA_GB and data["data_trend"] > DATA_TREND_GROWTH_MIN:
        pains.append(
            f"Data growing {data['data_trend']:+.0f} %/year — a tier sized for today may "
            "throttle within 12 months."
        )
    if data["voice_min"] < PAIN_LOW_VOICE_MIN and data["voice_trend"] < VOICE_TREND_DECLINE_MAX:
        pains.append(
            f"Voice falling {data['voice_trend']:+.0f} %/year — legacy minute bundles may be "
            "oversized; value shifts to data."
        )
    if data["roaming_days"] >= NARRATIVE_ROAMING_DAYS:
        pains.append(
            "Non-EU roaming costs if trips exceed the tariff's annual LG 2/3 data volume."
        )
    if rec.intent == "light" and rec.tariff.family == "prepaid":
        pains.append("A postpaid contract would likely be oversized for this usage.")
    if not pains:
        pains.append("Main risk is plan–usage mismatch at contract renewal.")

    upsells: list[str] = [
        f"Tariff fit → **{rec.tariff.name}** ({rec.tariff.data_label}) for a projected "
        f"need of ~{rec.data_need_gb:.0f} GB/month."
    ]
    if data["data_trend"] > DATA_TREND_GROWTH_MIN:
        upsells.append("Growing data → schedule a proactive tier review before throttling.")
    if rec.travel_relevant:
        upsells.append(
            "Frequent roaming → MagentaMobil L/XL annual non-EU volume; "
            "Travel & Surf passes only beyond it."
        )
    if data["voice_min"] >= UPSELL_VOICE_MIN:
        upsells.append(
            "Voice-heavy → German voice flat in every MagentaMobil tier; "
            "L/XL add calls to EU/CH/GB/TR."
        )
    if data["sms_count"] >= UPSELL_SMS:
        upsells.append(
            f"{data['sms_count']:.0f} SMS/month → confirm the current plan has an SMS flat "
            "(included in all MagentaMobil tiers)."
        )
    upsells.append(
        f"Household check → **{PLUSKARTE.name}** for extra devices, "
        f"**{MAGENTA_EINS.name}** with fixed line / TV."
    )
    return pains[:3], upsells[:5]


def render_profile_report(
    data: dict[str, float],
    *,
    scoring: ScoringResult | None = None,
) -> str:
    """Build profile markdown aligned with ``prompts/templates/run_profile.md``.

    When ``scoring`` is omitted, legacy L1 archetype distances are computed here.
    """
    if scoring is not None:
        distances = [(s.name, s.distance) for s in scoring.all_distances] or [
            (scoring.primary.name, scoring.primary.distance)
        ]
        overlays = list(scoring.overlays)
        confidence = scoring.confidence
    else:
        distances = compute_archetype_distances(data)
        overlays = compute_overlays(data)
        confidence = ""
    primary, primary_score = distances[0]
    secondary, secondary_score = distances[1] if len(distances) > 1 else ("", 0.0)
    if not confidence:
        confidence = confidence_label(primary_score, secondary_score)

    overlay_text = (
        "\n".join(f"- {o}" for o in overlays)
        if overlays
        else "*No overlays active — clear dominant archetype.*"
    )

    if secondary and secondary_score <= primary_score * SECONDARY_BLEND_SCORE_FACTOR:
        secondary_block = (
            f"\n### 3. Secondary archetype influence\n"
            f"Blend of **{primary}** with **{secondary}** traits. "
            f"Review both archetypes when choosing tariff and add-ons.\n"
        )
    else:
        secondary_block = (
            "\n### 3. Secondary archetype influence\n"
            "Secondary archetype is weak; treat the primary as decisive.\n"
        )

    narrative_bits: list[str] = []
    if data["data_gb"] >= NARRATIVE_HEAVY_DATA_GB:
        narrative_bits.append("heavy mobile data use")
    if data["voice_min"] >= NARRATIVE_HIGH_VOICE_MIN:
        narrative_bits.append("substantial voice calling")
    if data["sms_count"] >= NARRATIVE_HIGH_SMS:
        narrative_bits.append("frequent messaging")
    if data["roaming_days"] >= NARRATIVE_ROAMING_DAYS:
        narrative_bits.append("regular travel abroad")
    behaviour = (
        ", ".join(narrative_bits) if narrative_bits else "moderate, balanced mobile usage"
    )

    pains, upsells = usage_pains_and_upsells(data, scoring)

    return f"""### 1. Primary archetype
<mark>{primary}</mark> (proximity {primary_score:.3f}) — confidence: <mark>{confidence}</mark>.

### 2. Overlay characteristics
{overlay_text}
{secondary_block}
### 4. Lifestyle narrative
This subscriber shows **{behaviour}**. They use about <mark>{data["data_gb"]:.0f} GB</mark> data,
<mark>{data["voice_min"]:.0f}</mark> voice minutes, <mark>{data["sms_count"]:.0f}</mark> SMS, and
<mark>{data["roaming_days"]:.0f}</mark> roaming days per month. Data trend **{data["data_trend"]:+.0f} %/year**,
voice trend **{data["voice_trend"]:+.0f} %/year** (trajectory only).

### 5. Likely customer context
- {_ARCHETYPE_CONTEXT.get(primary, _ML_PROFILE_CONTEXT.get(primary, "Typical consumer mobile user."))}
- Contract review relevant if usage has shifted vs current plan.

### 6. Pain points & risks
{chr(10).join(f"- {p}" for p in pains)}

### 7. Upsell & retention signals
{chr(10).join(f"- {u}" for u in upsells)}
"""


def _usage_comparison_table(
    usage: Mapping[str, float],
    reference: Mapping[str, Any],
) -> str:
    """Customer's own usage next to the profile reference (centroid)."""
    rows = [
        ("Data (GB / month)", f"{usage['data_gb']:.0f}",
         f"{float(reference.get('avg_monthly_data_gb', 0)):.0f}"),
        ("Voice (min / month)", f"{usage['voice_min']:.0f}",
         f"{float(reference.get('avg_monthly_voice_min', 0)):.0f}"),
        ("SMS / month", f"{usage['sms_count']:.0f}",
         f"{float(reference.get('avg_monthly_sms', 0)):.0f}"),
        ("Roaming days / month", f"{usage['roaming_days']:.0f}",
         f"{float(reference.get('avg_roaming_days', 0)):.1f}"),
        ("Data trend (% / year)", f"{usage['data_trend']:+.0f}", "—"),
        ("Voice trend (% / year)", f"{usage['voice_trend']:+.0f}", "—"),
    ]
    body = "\n".join(f"| {name} | {cust} | {ref} |" for name, cust, ref in rows)
    return f"| Metric | This customer | Profile reference |\n|--------|---------------|-------------------|\n{body}"


def render_ml_profile_report(
    primary_label: str,
    usage: Mapping[str, float],
    overlays: Sequence[str],
    *,
    profile: dict[str, Any] | None = None,
    scoring: ScoringResult | None = None,
) -> str:
    """Profile markdown for the ML path: the customer's own numbers vs the profile reference."""
    overlay_text = (
        "\n".join(f"- {o}" for o in overlays)
        if overlays
        else "*No overlays active — clear dominant profile.*"
    )
    prof = profile or {}
    emoji = prof.get("emoji", "")
    signatures = prof.get("signature") or []
    examples = prof.get("examples") or []
    reference = prof.get("centroid") or {}

    sig_block = (
        "\n".join(f"- {s}" for s in signatures)
        if signatures
        else f"- {_ML_PROFILE_CONTEXT.get(primary_label, '')}"
    )
    ex_block = "\n".join(f"- {e}" for e in examples) if examples else "- —"
    title = f"{emoji} {primary_label}".strip() if emoji else primary_label
    confidence = f" — confidence: <mark>{scoring.confidence}</mark>" if scoring else ""
    secondary = ""
    if scoring and scoring.secondary:
        secondary = (
            f" Next closest: {scoring.secondary.name} "
            f"(distance {scoring.secondary.distance:.2f} vs {scoring.primary.distance:.2f})."
        )

    pains, upsells = usage_pains_and_upsells(usage, scoring)

    return f"""### 1. Primary usage profile
<mark>{title}</mark>{confidence} (K-Means segmentation, frozen centroids).{secondary}

### 2. Profile signature
{sig_block}

### 3. Overlay characteristics
{overlay_text}

### 4. Customer usage vs profile reference
{_usage_comparison_table(usage, reference)}

### 5. Example customer situations
{ex_block}

### 6. Pain points & risks
{chr(10).join(f"- {p}" for p in pains)}

### 7. Upsell & retention signals
{chr(10).join(f"- {u}" for u in upsells)}
"""
