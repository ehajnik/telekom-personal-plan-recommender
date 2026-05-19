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


def build_profile_prompt(data: dict[str, float]) -> str:
    distances = compute_archetype_distances(data)
    scoring = build_scoring_result(CustomerUsage.from_mapping(data))
    return _fill_template(
        _read_text(str(PROMPT_TEMPLATES_DIR / "run_profile.md")),
        {
            "slider_features": format_slider_features(data),
            "centroid_distances": format_centroid_distances(distances),
            "overlay_signals": format_overlay_signals(compute_overlays(data)),
            "profile_characteristics": _read_text(str(DATA_DIR / "consumer_archetypes.md")),
            "required_primary": scoring.primary_name,
            "required_confidence": scoring.confidence,
        },
    )


def build_offer_prompt(customer_profile: str) -> str:
    return _fill_template(
        _read_text(str(PROMPT_TEMPLATES_DIR / "run_offer.md")),
        {
            "customer_profile": customer_profile,
            "tariffs_and_options": _read_text(str(DATA_DIR / "tariffs_private.md")),
        },
    )
