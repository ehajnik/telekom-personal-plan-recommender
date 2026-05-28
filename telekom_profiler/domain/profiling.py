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
<mark>{primary}</mark> (proximity {primary_score:.3f}) — confidence: <mark>{confidence}</mark>.

### 2. Overlay characteristics
{overlay_text}
{secondary_block}
### 4. Lifestyle narrative
This subscriber shows **{behaviour}**. They use about <mark>{data["data_gb"]:.0f} GB</mark> data,
<mark>{data["voice_min"]:.0f}</mark> voice minutes, <mark>{data["sms_count"]:.0f}</mark> SMS, and
<mark>{data["roaming_days"]:.0f}</mark> roaming days per month. Data trend **{data["data_trend"]:+.0f}**,
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
    "Value optimization candidate": "Broad engagement suggests plan-fit optimization opportunity.",
}


def _format_centroid_table(centroid: dict[str, float]) -> str:
    rows = [
        ("Lines (total / active)", f"{centroid.get('lines_total', 0):.0f} / {centroid.get('lines_active', 0):.0f}"),
        ("Active line ratio", f"{centroid.get('active_line_ratio', 0):.3f}"),
        ("Data (GB / month)", f"{centroid.get('avg_monthly_data_gb', 0):.1f}"),
        ("Voice (min / month)", f"{centroid.get('avg_monthly_voice_min', 0):.0f}"),
        ("SMS / month", f"{centroid.get('avg_monthly_sms', 0):.0f}"),
        ("Idle line share", f"{centroid.get('pct_idle_lines', 0):.1%}"),
        ("Roaming days / month", f"{centroid.get('avg_roaming_days', 0):.1f}"),
        ("Roaming days ratio", f"{centroid.get('roaming_days_ratio', 0):.3f}"),
        ("Countries visited", f"{centroid.get('countries_visited', 0):.1f}"),
        ("Roaming intensity", f"{centroid.get('roaming_intensity', 0):.2f}"),
        ("Session intensity", f"{centroid.get('session_intensity', 0):.0f}"),
        ("Data per active line (GB)", f"{centroid.get('data_per_active_line', 0):.1f}"),
        ("Plan tier / usage gap", f"{centroid.get('plan_tier', 0):.1f} / {centroid.get('plan_usage_gap', 0):.2f}"),
        ("Data trend / month", f"{centroid.get('mean_data_trend_per_month', 0):+.1f}"),
        ("Voice trend / month", f"{centroid.get('mean_voice_trend_per_month', 0):+.1f}"),
        ("Roaming trend / month", f"{centroid.get('mean_roaming_trend_per_month', 0):+.2f}"),
    ]
    body = "\n".join(f"| {name} | {val} |" for name, val in rows)
    return f"| Metric | Value |\n|--------|-------|\n{body}"


def render_ml_profile_report(
    primary_label: str,
    metrics: dict[str, float],
    overlays: tuple[str, ...] | list[str],
    *,
    profile: dict | None = None,
) -> str:
    """Profile markdown with concrete 12-month metrics (ML path)."""
    overlay_text = (
        "\n".join(f"- {o}" for o in overlays)
        if overlays
        else "*No overlays active — clear dominant profile.*"
    )
    prof = profile or {}
    emoji = prof.get("emoji", "")
    signatures = prof.get("signature") or []
    examples = prof.get("examples") or []
    centroid = prof.get("centroid") or metrics

    sig_block = "\n".join(f"- {s}" for s in signatures) if signatures else f"- {_ML_PROFILE_CONTEXT.get(primary_label, '')}"
    ex_block = "\n".join(f"- {e}" for e in examples) if examples else "- —"
    title = f"{emoji} {primary_label}".strip() if emoji else primary_label

    return f"""### 1. Primary usage profile
**{title}** (K-Means segmentation on 12-month baseline features).

### 2. Profile signature
{sig_block}

### 3. Overlay characteristics
{overlay_text}

### 4. Example customer situations
{ex_block}

### 5. Centroid metrics (12-month baseline)
{_format_centroid_table(centroid)}

### 6. Pain points & risks
- Plan–usage mismatch if current tier diverges from centroid metrics.
- Review roaming packs if travel-heavy overlay is active.

### 7. Upsell & retention signals
- Align catalog SKU to primary profile and active overlays (see offer step).
"""
