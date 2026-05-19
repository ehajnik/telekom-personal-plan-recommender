"""Rule-based B2C customer profile generation."""

from __future__ import annotations

from telekom_profiler.config.thresholds import (
    DATA_TREND_GROWTH_MIN,
    NARRATIVE_HEAVY_DATA_GB,
    NARRATIVE_HIGH_SMS,
    NARRATIVE_HIGH_VOICE_MIN,
    NARRATIVE_ROAMING_DAYS,
    PAIN_DATA_GB,
    PAIN_LOW_VOICE_MIN,
    SECONDARY_BLEND_SCORE_FACTOR,
    UPSELL_DATA_GB,
    UPSELL_SMS,
    UPSELL_VOICE_MIN,
    VOICE_TREND_DECLINE_MAX,
)
from telekom_profiler.domain.archetypes import (
    compute_archetype_distances,
    compute_overlays,
    confidence_label,
)

_ARCHETYPE_CONTEXT: dict[str, str] = {
    "Streamer": "Young professional or household streaming on mobile.",
    "Chatterbox": "Voice-first user, possibly older demographic or tradesperson.",
    "Essential": "Price-conscious user with basic smartphone needs.",
    "Roamer": "Cross-border commuter or frequent leisure traveller.",
    "Messenger": "Messaging-centric, social and chat app usage.",
}


def render_profile_report(data: dict[str, float]) -> str:
    """Build profile markdown aligned with ``prompts/templates/run_profile.md``."""
    distances = compute_archetype_distances(data)
    primary, primary_score = distances[0]
    secondary, secondary_score = distances[1] if len(distances) > 1 else ("", 0.0)
    overlays = compute_overlays(data)
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

    pains: list[str] = []
    if data["data_gb"] > PAIN_DATA_GB and data["data_trend"] > DATA_TREND_GROWTH_MIN:
        pains.append("Risk of out-of-bundle data charges if tier is too small.")
    if data["voice_min"] < PAIN_LOW_VOICE_MIN and data["voice_trend"] < VOICE_TREND_DECLINE_MAX:
        pains.append("Paying for unused inclusive voice minutes.")
    if data["roaming_days"] >= NARRATIVE_ROAMING_DAYS:
        pains.append("Roaming surcharges if EU/world packs are missing.")
    if not pains:
        pains.append("Main risk is plan–usage mismatch at contract renewal.")

    upsells: list[str] = []
    if data["data_gb"] >= UPSELL_DATA_GB:
        upsells.append("High data → consider **MagentaMobil L/XL** or **Data Boost**.")
    if data["roaming_days"] >= NARRATIVE_ROAMING_DAYS:
        upsells.append("Frequent roaming → **EU Roaming Plus** or **World Roaming Pack**.")
    if data["voice_min"] >= UPSELL_VOICE_MIN:
        upsells.append("Voice-heavy → ensure flat voice in **MagentaMobil M+**.")
    if data["data_trend"] > DATA_TREND_GROWTH_MIN:
        upsells.append("Growing data → proactive tier upgrade before bill shock.")
    if data["sms_count"] >= UPSELL_SMS:
        upsells.append("Messaging-heavy → unlimited SMS bundles in postpaid tiers.")

    return f"""### 1. Primary archetype
**{primary}** (proximity {primary_score:.3f}) — confidence: **{confidence}**.

### 2. Overlay characteristics
{overlay_text}
{secondary_block}
### 4. Lifestyle narrative
This subscriber shows **{behaviour}**. They use about **{data["data_gb"]:.0f} GB** data,
**{data["voice_min"]:.0f}** voice minutes, **{data["sms_count"]:.0f}** SMS, and
**{data["roaming_days"]:.0f}** roaming days per month. Data trend **{data["data_trend"]:+.0f}**,
voice trend **{data["voice_trend"]:+.0f}** (trajectory only).

### 5. Likely customer context
- {_ARCHETYPE_CONTEXT.get(primary, "Typical consumer mobile user.")}
- Contract review relevant if usage has shifted vs current plan.

### 6. Pain points & risks
{chr(10).join(f"- {p}" for p in pains[:3])}

### 7. Upsell & retention signals
{chr(10).join(f"- {u}" for u in upsells[:5])}
"""


_ML_PROFILE_CONTEXT: dict[str, str] = {
    "Light / occasional user": "Low-intensity mobile user; prepaid or entry postpaid fit.",
    "Streaming & data-heavy": "High data and session intensity; unlimited or large buckets.",
    "Voice-centric": "Voice-first; moderate data; flat domestic voice important.",
    "Roaming / travel-heavy": "Frequent international travel; roaming packs essential.",
    "Underutilized / overspending": "Paying for capacity beyond actual use; downgrade opportunity.",
}


def render_ml_profile_report(
    primary_label: str,
    metrics: dict[str, float],
    overlays: tuple[str, ...] | list[str],
) -> str:
    """Profile markdown with concrete 12-month metrics (ML path)."""
    overlay_text = (
        "\n".join(f"- {o}" for o in overlays)
        if overlays
        else "*No overlays active — clear dominant profile.*"
    )
    ctx = _ML_PROFILE_CONTEXT.get(primary_label, "Consumer mobile subscriber.")
    return f"""### 1. Primary usage profile
**{primary_label}** (K-Means segmentation on 12-month baseline features).

### 2. Overlay characteristics
{overlay_text}

### 3. Measured usage (12-month averages)
| Metric | Value |
|--------|-------|
| Data | **{metrics.get("avg_monthly_data_gb", 0):.1f} GB** / month |
| Voice | **{metrics.get("avg_monthly_voice_min", 0):.0f} min** / month |
| SMS | **{metrics.get("avg_monthly_sms", 0):.0f}** / month |
| Roaming days | **{metrics.get("avg_roaming_days", 0):.1f}** |
| Countries visited | **{metrics.get("countries_visited", 0):.1f}** |
| Active line ratio | **{metrics.get("active_line_ratio", 0):.2f}** |
| Idle line share | **{metrics.get("pct_idle_lines", 0):.0%}** |
| Session intensity | **{metrics.get("session_intensity", 0):.0f}** |

### 4. Customer context
- {ctx}
- Segmentation based on baseline behaviour; trends shown as overlays only.

### 5. Pain points & risks
- Plan–usage mismatch if current tier diverges from metrics above.
- Review roaming packs if travel-heavy overlay is active.

### 6. Upsell & retention signals
- Align catalog SKU to primary profile and active overlays (see offer step).
"""
