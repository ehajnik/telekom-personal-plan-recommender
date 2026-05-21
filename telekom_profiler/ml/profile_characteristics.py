"""Build and load profile_characteristics.json (enterprise-style schema)."""

from __future__ import annotations

import json
from typing import Any

from telekom_profiler.ml.schema import (
    DATA_TREND_GROWING_MIN,
    DATA_TREND_SHRINKING_MAX,
    LINES_TREND_GROWING_MIN,
    MIXED_PROFILE_RATIO,
    PROFILE_EMOJI,
    ROAMING_TREND_GROWING_MIN,
    VOICE_TREND_DECLINING_MAX,
)

PROFILE_SIGNATURES: dict[str, list[str]] = {
    "Light / occasional user": [
        "Low monthly data and voice",
        "Few roaming days",
        "Single-line household typical",
        "Minimal session intensity",
    ],
    "Streaming & data-heavy": [
        "Very high mobile data (tens of GB/month)",
        "Elevated session intensity",
        "Evening and weekend usage peaks",
        "Moderate voice, low roaming",
    ],
    "Voice-centric": [
        "High call minutes per line",
        "Low data usage",
        "Domestic voice-heavy behaviour",
    ],
    "Roaming / travel-heavy": [
        "High roaming days per month",
        "Many countries visited",
        "Mix of data and voice while abroad",
    ],
    "Underutilized / overspending": [
        "High proportion of idle lines",
        "Plan tier above actual usage",
        "Low data per active line",
        "Downgrade / rightsizing opportunity",
    ],
    "Family / multi-line": [
        "Multi-line household (3-5 SIMs, most active)",
        "Combined family data and voice consumption",
        "Mid-to-upper plan tier with shared allowances",
        "Some incidental roaming for holidays",
    ],
}

PROFILE_EXAMPLES: dict[str, list[str]] = {
    "Light / occasional user": [
        "Occasional smartphone user",
        "Secondary SIM for emergencies",
        "Prepaid light user",
    ],
    "Streaming & data-heavy": [
        "Mobile streaming and gaming",
        "Remote work on mobile hotspot",
        "Heavy social video consumption",
    ],
    "Voice-centric": [
        "Older demographic voice-first",
        "Tradesperson on calls all day",
        "Low smartphone data needs",
    ],
    "Roaming / travel-heavy": [
        "Cross-border commuter",
        "Frequent leisure traveller",
        "International sales rep",
    ],
    "Underutilized / overspending": [
        "Family plan with unused lines",
        "Legacy tier after usage drop",
        "Multi-SIM with idle secondary lines",
    ],
    "Family / multi-line": [
        "Parents and teens on a shared MagentaMobil tariff",
        "PlusKarte add-ons for additional household lines",
        "Mid-sized family with mixed voice and streaming usage",
    ],
}


def build_centroid(row: dict[str, float]) -> dict[str, float]:
    """Full centroid metrics for a cluster (12-month baseline + trends)."""
    data_trend = float(row.get("data_trend", 0)) * 50.0
    voice_trend = float(row.get("voice_trend", 0)) * 50.0
    roaming_trend = float(row.get("roaming_trend", 0)) * 30.0
    lines_trend = float(row.get("lines_trend", 0))

    return {
        "lines_total": round(float(row.get("lines_total_mean", 1)), 2),
        "lines_active": round(float(row.get("lines_active_mean", 1)), 2),
        "active_line_ratio": round(float(row.get("active_line_ratio", 1)), 3),
        "avg_monthly_data_gb": round(float(row.get("data_gb_mean", 0)), 1),
        "avg_monthly_voice_min": round(float(row.get("voice_min_mean", 0)), 1),
        "avg_monthly_sms": round(float(row.get("sms_count_mean", 0)), 1),
        "pct_idle_lines": round(float(row.get("pct_idle_lines", 0)), 3),
        "roaming_days_ratio": round(float(row.get("roaming_days_ratio", 0)), 3),
        "avg_roaming_days": round(float(row.get("roaming_days_mean", 0)), 1),
        "countries_visited": round(float(row.get("countries_visited_mean", 0)), 1),
        "avg_session_mb": round(float(row.get("avg_session_mb_mean", 0)), 1),
        "active_days_per_month": round(float(row.get("active_days_mean", 0)), 1),
        "plan_tier": round(float(row.get("plan_tier_mean", 0)), 1),
        "roaming_intensity": round(float(row.get("roaming_intensity", 0)), 2),
        "data_per_active_line": round(float(row.get("data_per_active_line", 0)), 1),
        "session_intensity": round(float(row.get("session_intensity", 0)), 1),
        "evening_peak_share": round(float(row.get("evening_peak_share", 0)), 3),
        "weekend_share": round(float(row.get("weekend_share", 0)), 3),
        "plan_usage_gap": round(float(row.get("plan_usage_gap", 0)), 2),
        "mean_data_trend_per_month": round(data_trend, 1),
        "mean_voice_trend_per_month": round(voice_trend, 1),
        "mean_roaming_trend_per_month": round(roaming_trend, 2),
        "mean_lines_trend_per_month": round(lines_trend, 2),
    }


def ui_slider_defaults_from_row(row: dict[str, float]) -> dict[str, int]:
    """Gradio slider positions derived from centroid row."""
    return {
        "data_gb": int(min(150, max(0, round(row.get("data_gb_mean", 30))))),
        "voice_min": int(min(3000, max(0, round(row.get("voice_min_mean", 400))))),
        "sms_count": int(min(500, max(0, round(row.get("sms_count_mean", 50))))),
        "roaming_days": int(min(30, max(0, round(row.get("roaming_days_mean", 2))))),
        "data_trend": int(min(50, max(-50, round(float(row.get("data_trend", 0)) * 50)))),
        "voice_trend": int(
            min(50, max(-50, round(float(row.get("voice_trend", 0)) * 50)))
        ),
    }


def overlay_thresholds() -> dict[str, float]:
    """Overlay tuning exported alongside profiles (mirrors enterprise PoC)."""
    return {
        "mixed_profile_ratio": MIXED_PROFILE_RATIO,
        "data_growth_threshold": DATA_TREND_GROWING_MIN * 50,
        "data_decline_threshold": DATA_TREND_SHRINKING_MAX * 50,
        "voice_decline_threshold": VOICE_TREND_DECLINING_MAX * 50,
        "roaming_growth_threshold": ROAMING_TREND_GROWING_MIN,
        "lines_growth_threshold": LINES_TREND_GROWING_MIN,
    }


def _auto_signature_from_row(row: dict[str, float]) -> list[str]:
    """Synthesise a short bullet list describing a centroid from feature rules.

    Used for clusters that K-Means discovers but no named ``PROFILE_LABELS``
    entry matched (i.e. ``Profile N`` placeholders when ``k`` exceeds the
    number of named labels).
    """
    data = float(row.get("data_gb_mean", 0))
    voice = float(row.get("voice_min_mean", 0))
    lines_total = float(row.get("lines_total_mean", 1))
    pct_idle = float(row.get("pct_idle_lines", 0))
    roaming = float(row.get("roaming_days_mean", 0))
    plan = float(row.get("plan_tier_mean", 0))

    sig: list[str] = []
    if data >= 80:
        sig.append("Very high mobile data usage")
    elif data >= 30:
        sig.append("Elevated mobile data usage")
    elif data < 5:
        sig.append("Low mobile data usage")
    if voice >= 800:
        sig.append("Heavy voice usage")
    elif voice >= 300:
        sig.append("Moderate voice usage")
    elif voice < 100:
        sig.append("Low voice usage")
    if lines_total >= 2.5:
        sig.append("Multi-line household or small business")
    elif lines_total >= 1.5:
        sig.append("Multiple lines on the account")
    if pct_idle >= 0.4:
        sig.append("Significant share of idle lines")
    if roaming >= 10:
        sig.append("Frequent international roaming")
    elif roaming >= 5:
        sig.append("Occasional international roaming")
    if plan >= 4:
        sig.append("Premium plan tier")
    elif plan and plan <= 1.5:
        sig.append("Entry-level plan tier")
    if not sig:
        sig.append("Mixed usage profile")
    return sig


def build_profile_entry(
    label: str,
    cluster_idx: int,
    row: dict[str, float],
) -> dict[str, Any]:
    """Single profile block under ``profiles``.

    Named ``PROFILE_LABELS`` use the curated ``PROFILE_SIGNATURES`` /
    ``PROFILE_EXAMPLES``; auto-discovered ``Profile N`` clusters fall back to a
    rules-based signature derived from the centroid so the JSON is never
    contradictory.
    """
    centroid = build_centroid(row)
    is_named = label in PROFILE_SIGNATURES
    signature = (
        list(PROFILE_SIGNATURES[label]) if is_named else _auto_signature_from_row(row)
    )
    examples = (
        list(PROFILE_EXAMPLES[label]) if label in PROFILE_EXAMPLES else ["Auto-discovered cluster"]
    )
    emoji = PROFILE_EMOJI.get(label, "🧩" if not is_named else "📱")
    return {
        "emoji": emoji,
        "cluster_idx": cluster_idx,
        "signature": signature,
        "examples": examples,
        "centroid": centroid,
        "slider_defaults": ui_slider_defaults_from_row(row),
    }


def build_profile_characteristics_document(
    profiles_by_label: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Top-level JSON written to artifacts/profile_characteristics.json."""
    return {
        "profiles": profiles_by_label,
        "overlays": overlay_thresholds(),
    }


def load_profiles_document(raw: dict[str, Any] | None = None) -> dict[str, Any]:
    """Load from parsed JSON; supports legacy flat profile map."""
    if raw is None:
        return {"profiles": {}, "overlays": overlay_thresholds()}
    if "profiles" in raw:
        return raw
    return {"profiles": raw, "overlays": overlay_thresholds()}


def get_profile(raw: dict[str, Any], label: str) -> dict[str, Any]:
    """Return one profile dict by label."""
    doc = load_profiles_document(raw)
    return dict(doc.get("profiles", {}).get(label, {}))


def metrics_from_centroid(centroid: dict[str, float]) -> dict[str, float]:
    """Narrative metrics for UI / reports from centroid block."""
    return {
        "avg_monthly_data_gb": float(centroid.get("avg_monthly_data_gb", 0)),
        "avg_monthly_voice_min": float(centroid.get("avg_monthly_voice_min", 0)),
        "avg_monthly_sms": float(centroid.get("avg_monthly_sms", 0)),
        "avg_roaming_days": float(centroid.get("avg_roaming_days", 0)),
        "countries_visited": float(centroid.get("countries_visited", 0)),
        "active_line_ratio": float(centroid.get("active_line_ratio", 0)),
        "pct_idle_lines": float(centroid.get("pct_idle_lines", 0)),
        "session_intensity": float(centroid.get("session_intensity", 0)),
    }


def format_profiles_for_prompt(doc: dict[str, Any]) -> str:
    """Human-readable profile reference for LLM prompts."""
    loaded = load_profiles_document(doc)
    lines: list[str] = []
    for label, prof in loaded.get("profiles", {}).items():
        emoji = prof.get("emoji", "")
        sig = prof.get("signature", [])
        ex = prof.get("examples", [])
        c = prof.get("centroid", {})
        lines.append(f"### {emoji} {label}")
        if sig:
            lines.append("**Signals:** " + "; ".join(sig))
        if ex:
            lines.append("**Examples:** " + ", ".join(ex))
        if c:
            lines.append(
                f"**Centroid:** {c.get('avg_monthly_data_gb', 0):.0f} GB data, "
                f"{c.get('avg_monthly_voice_min', 0):.0f} voice min, "
                f"{c.get('avg_roaming_days', 0):.1f} roaming days, "
                f"{c.get('pct_idle_lines', 0):.0%} idle lines."
            )
        lines.append("")
    return "\n".join(lines).strip()


def read_profile_characteristics(path: str) -> dict[str, Any]:
    """Load JSON file from disk."""
    from pathlib import Path

    return json.loads(Path(path).read_text(encoding="utf-8"))
