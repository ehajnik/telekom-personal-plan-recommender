"""
Typed domain objects for customer usage and profiling results.

These models are the stable contract between UI, services, and future BSS/CRM
integrations. Prefer passing ``CustomerUsage`` and ``ProfileResult`` instead of
unstructured dicts or markdown strings when wiring new code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Self

from telekom_profiler.config.sliders import SLIDER_KEYS, TREND_SLIDERS, USAGE_SLIDERS


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
    def from_mapping(cls, data: Mapping[str, float]) -> Self:
        """Build from a slider dict or partial API payload; missing keys raise ``KeyError``."""
        return cls(**{key: float(data[key]) for key in SLIDER_KEYS})

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
    def defaults(cls) -> Self:
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
