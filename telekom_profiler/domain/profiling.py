"""Rule-based B2C customer profile generation."""

from __future__ import annotations

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

    if secondary and secondary_score <= primary_score * 1.3:
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
    if data["data_gb"] >= 60:
        narrative_bits.append("heavy mobile data use")
    if data["voice_min"] >= 800:
        narrative_bits.append("substantial voice calling")
    if data["sms_count"] >= 100:
        narrative_bits.append("frequent messaging")
    if data["roaming_days"] >= 8:
        narrative_bits.append("regular travel abroad")
    behaviour = (
        ", ".join(narrative_bits) if narrative_bits else "moderate, balanced mobile usage"
    )

    pains: list[str] = []
    if data["data_gb"] > 40 and data["data_trend"] > 10:
        pains.append("Risk of out-of-bundle data charges if tier is too small.")
    if data["voice_min"] < 200 and data["voice_trend"] < -10:
        pains.append("Paying for unused inclusive voice minutes.")
    if data["roaming_days"] >= 8:
        pains.append("Roaming surcharges if EU/world packs are missing.")
    if not pains:
        pains.append("Main risk is plan–usage mismatch at contract renewal.")

    upsells: list[str] = []
    if data["data_gb"] >= 50:
        upsells.append("High data → consider **MagentaMobil L/XL** or **Data Boost**.")
    if data["roaming_days"] >= 8:
        upsells.append("Frequent roaming → **EU Roaming Plus** or **World Roaming Pack**.")
    if data["voice_min"] >= 1000:
        upsells.append("Voice-heavy → ensure flat voice in **MagentaMobil M+**.")
    if data["data_trend"] > 10:
        upsells.append("Growing data → proactive tier upgrade before bill shock.")
    if data["sms_count"] >= 100:
        upsells.append("Messaging-heavy → unlimited SMS bundles in postpaid tiers.")

    return f"""### 1. Primary archetype
**{primary}** (proximity {primary_score:.3f}) — confidence: **{confidence}**.

### 2. Overlay characteristics
{overlay_text}
{secondary_block}
### 4. Lifestyle narrative
This subscriber shows **{behaviour}**. They use about **{data["data_gb"]:.0f} GB** data, **{data["voice_min"]:.0f}** voice minutes, **{data["sms_count"]:.0f}** SMS, and **{data["roaming_days"]:.0f}** roaming days per month. Data trend **{data["data_trend"]:+.0f}**, voice trend **{data["voice_trend"]:+.0f}** (trajectory only).

### 5. Likely customer context
- {_ARCHETYPE_CONTEXT.get(primary, "Typical consumer mobile user.")}
- Contract review relevant if usage has shifted vs current plan.

### 6. Pain points & risks
{chr(10).join(f"- {p}" for p in pains[:3])}

### 7. Upsell & retention signals
{chr(10).join(f"- {u}" for u in upsells[:5])}
"""
