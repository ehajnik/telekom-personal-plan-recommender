"""Assemble LLM prompts from templates and runtime slider data."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from telekom_profiler.domain.archetypes import compute_archetype_distances, compute_overlays
from telekom_profiler.domain.models import CustomerUsage
from telekom_profiler.domain.scoring import build_scoring_result
from telekom_profiler.paths import DATA_DIR, PROMPT_TEMPLATES_DIR


@lru_cache(maxsize=16)
def _read_text(path_str: str) -> str:
    return Path(path_str).read_text(encoding="utf-8")


def _fill_template(template: str, mapping: dict[str, str]) -> str:
    result = template
    for key, value in mapping.items():
        result = result.replace(f"{{{key}}}", value)
    return result


def format_slider_features(data: dict[str, float]) -> str:
    return "\n".join(
        [
            f"data_gb: {data['data_gb']:.0f} GB / month",
            f"voice_min: {data['voice_min']:.0f} minutes / month",
            f"sms_count: {data['sms_count']:.0f} SMS / month",
            f"roaming_days: {data['roaming_days']:.0f} days abroad / month",
            f"data_trend: {data['data_trend']:+.0f} (trajectory, not clustering input)",
            f"voice_trend: {data['voice_trend']:+.0f} (trajectory, not clustering input)",
        ]
    )


def format_centroid_distances(distances: list[tuple[str, float]]) -> str:
    return "\n".join(f"{name}: {score:.3f}" for name, score in distances)


def format_overlay_signals(overlays: list[str]) -> str:
    if not overlays:
        return "None active"
    return "\n".join(f"- {flag}" for flag in overlays)


def format_distance_table(scoring: object) -> str:
    """All cluster distances from ``ScoringResult``."""
    from telekom_profiler.domain.models import ScoringResult

    if not isinstance(scoring, ScoringResult) or not scoring.all_distances:
        return "N/A"
    return "\n".join(
        f"| {s.name} | {s.distance:.3f} |" for s in scoring.all_distances
    )


def build_profile_prompt(
    data: dict[str, float],
    *,
    metrics_block: str = "",
) -> str:
    usage = CustomerUsage.from_mapping(data)
    scoring = build_scoring_result(usage)
    distances = [(s.name, s.distance) for s in scoring.all_distances] or list(
        compute_archetype_distances(data)
    )
    overlays = list(scoring.overlays) if scoring.overlays else compute_overlays(data)
    chars_path = DATA_DIR / "consumer_archetypes.md"
    if not chars_path.is_file():
        chars_path = DATA_DIR / "plans_and_options.md"
    return _fill_template(
        _read_text(str(PROMPT_TEMPLATES_DIR / "run_profile.md")),
        {
            "slider_features": format_slider_features(data),
            "centroid_distances": format_centroid_distances(distances),
            "distance_table": format_distance_table(scoring),
            "overlay_signals": format_overlay_signals(overlays),
            "profile_characteristics": _read_text(str(chars_path)),
            "required_primary": scoring.primary_name,
            "required_confidence": scoring.confidence,
            "metrics_block": metrics_block or "_No extended metrics._",
        },
    )


def build_offer_prompt(
    customer_profile: str,
    *,
    scoring: object | None = None,
) -> str:
    catalog = DATA_DIR / "plans_and_options.md"
    if not catalog.is_file():
        catalog = DATA_DIR / "tariffs_private.md"
    overlay_line = ""
    if scoring is not None and hasattr(scoring, "overlays"):
        overlay_line = format_overlay_signals(list(scoring.overlays))
    return _fill_template(
        _read_text(str(PROMPT_TEMPLATES_DIR / "run_offer.md")),
        {
            "customer_profile": customer_profile,
            "tariffs_and_options": _read_text(str(catalog)),
            "overlay_signals": overlay_line or "None",
            "primary_profile": getattr(scoring, "primary_name", "Unknown"),
        },
    )
