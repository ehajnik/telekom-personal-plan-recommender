"""
Typed domain objects for customer usage and profiling results.

These models are the stable contract between UI, services, and future BSS/CRM
integrations. Prefer passing ``CustomerUsage`` and ``ProfileResult`` instead of
unstructured dicts or markdown strings when wiring new code.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from telekom_profiler.config.sliders import SLIDER_KEYS, TREND_SLIDERS, USAGE_SLIDERS


def _slider_bounds() -> dict[str, tuple[float, float]]:
    """Map slider key to (minimum, maximum)."""
    specs = {**USAGE_SLIDERS, **TREND_SLIDERS}
    return {key: (float(spec[1]), float(spec[2])) for key, spec in specs.items()}


@dataclass(frozen=True, slots=True)
class CustomerUsage:
    """Monthly usage snapshot from sliders or an external billing feed."""

    data_gb: float
    voice_min: float
    sms_count: float
    roaming_days: float
    data_trend: float
    voice_trend: float

    @classmethod
    def from_mapping(cls, data: Mapping[str, float], *, clamp: bool = False) -> CustomerUsage:
        """
        Build from a slider dict or API payload.

        Missing keys raise ``KeyError``. When ``clamp`` is True, values are
        clipped to UI slider min/max.
        """
        bounds = _slider_bounds()
        values: dict[str, float] = {}
        for key in SLIDER_KEYS:
            if key not in data:
                raise KeyError(f"Missing required usage key: {key}")
            value = float(data[key])
            if clamp:
                lo, hi = bounds[key]
                value = max(lo, min(hi, value))
            values[key] = value
        return cls(**values)

    def validate(self) -> None:
        """Raise ``ValueError`` if any field is outside slider bounds."""
        bounds = _slider_bounds()
        for key in SLIDER_KEYS:
            value = getattr(self, key)
            lo, hi = bounds[key]
            if not lo <= value <= hi:
                raise ValueError(
                    f"{key}={value} is outside allowed range [{lo}, {hi}]"
                )

    def as_dict(self) -> dict[str, float]:
        """Plain dict for legacy callers and prompt builders."""
        return {
            "data_gb": self.data_gb,
            "voice_min": self.voice_min,
            "sms_count": self.sms_count,
            "roaming_days": self.roaming_days,
            "data_trend": self.data_trend,
            "voice_trend": self.voice_trend,
        }

    def usage_values(self) -> tuple[float, float, float, float]:
        """Usage dimensions only, in archetype key order."""
        return (self.data_gb, self.voice_min, self.sms_count, self.roaming_days)

    @classmethod
    def defaults(cls) -> CustomerUsage:
        """Default slider positions (demo / reset)."""
        values = {key: float(spec[3]) for key, spec in {**USAGE_SLIDERS, **TREND_SLIDERS}.items()}
        return cls.from_mapping(values)


@dataclass(frozen=True, slots=True)
class ArchetypeScore:
    """Single archetype proximity result (lower distance = closer match)."""

    name: str
    distance: float


@dataclass(frozen=True, slots=True)
class ScoringResult:
    """Deterministic archetype scoring output (independent of LLM narrative)."""

    primary: ArchetypeScore
    secondary: ArchetypeScore | None
    all_distances: tuple[ArchetypeScore, ...] = ()
    overlays: tuple[str, ...] = ()
    confidence: str = "Medium"

    @property
    def primary_name(self) -> str:
        return self.primary.name


@dataclass(frozen=True, slots=True)
class ProfileResult:
    """Customer profile artefact returned by any profile provider."""

    markdown: str
    usage: CustomerUsage
    scoring: ScoringResult | None = None
    source: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_placeholder(self) -> bool:
        from telekom_profiler.config.sliders import PLACEHOLDER_PREFIX

        text = self.markdown.strip()
        return not text or text.startswith(PLACEHOLDER_PREFIX)

    def to_state_dict(self) -> dict[str, Any]:
        """JSON-serializable dict for Gradio ``gr.State``."""
        scoring_dict = None
        if self.scoring is not None:
            scoring_dict = {
                "primary": {
                    "name": self.scoring.primary.name,
                    "distance": self.scoring.primary.distance,
                },
                "secondary": (
                    {
                        "name": self.scoring.secondary.name,
                        "distance": self.scoring.secondary.distance,
                    }
                    if self.scoring.secondary
                    else None
                ),
                "confidence": self.scoring.confidence,
                "overlays": list(self.scoring.overlays),
            }
        return {
            "markdown": self.markdown,
            "usage": self.usage.as_dict(),
            "source": self.source,
            "metadata": dict(self.metadata),
            "scoring": scoring_dict,
        }

    @classmethod
    def from_state_dict(cls, data: dict[str, Any] | None) -> ProfileResult | None:
        """Restore from Gradio state; returns None if empty."""
        if not data or not data.get("markdown"):
            return None
        usage = CustomerUsage.from_mapping(data["usage"])
        scoring = None
        raw_scoring = data.get("scoring")
        if raw_scoring and raw_scoring.get("primary"):
            primary = ArchetypeScore(
                raw_scoring["primary"]["name"],
                float(raw_scoring["primary"]["distance"]),
            )
            secondary = None
            if raw_scoring.get("secondary"):
                secondary = ArchetypeScore(
                    raw_scoring["secondary"]["name"],
                    float(raw_scoring["secondary"]["distance"]),
                )
            scoring = ScoringResult(
                primary=primary,
                secondary=secondary,
                overlays=tuple(raw_scoring.get("overlays") or []),
                confidence=raw_scoring.get("confidence", "Medium"),
            )
        return cls(
            markdown=data["markdown"],
            usage=usage,
            scoring=scoring,
            source=data.get("source", "unknown"),
            metadata=dict(data.get("metadata") or {}),
        )
