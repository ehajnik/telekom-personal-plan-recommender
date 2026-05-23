"""
Profiler engine — orchestrates profile and offer providers.

Use ``ProfilerEngine`` in services, notebooks, or batch jobs. Inject custom
``ProfileProvider`` / ``OfferProvider`` implementations for integration tests
or production backends.
"""

from __future__ import annotations

from collections.abc import Mapping

from telekom_profiler.domain.models import CustomerUsage, ProfileResult
from telekom_profiler.domain.scoring import build_scoring_result
from telekom_profiler.services.protocols import OfferProvider, ProfileProvider
from telekom_profiler.services.providers import (
    default_offer_provider,
    default_profile_provider,
)


def _normalize_usage(
    usage: CustomerUsage | Mapping[str, float],
    *,
    clamp: bool = True,
) -> CustomerUsage:
    """Validate and optionally clamp usage before profiling or offers."""
    if isinstance(usage, CustomerUsage):
        customer = (
            CustomerUsage.from_mapping(usage.as_dict(), clamp=True)
            if clamp
            else usage
        )
    else:
        customer = CustomerUsage.from_mapping(usage, clamp=clamp)
    customer.validate()
    return customer


class ProfilerEngine:
    """Coordinates profiling and offer steps with swappable backends."""

    def __init__(
        self,
        profile_provider: ProfileProvider | None = None,
        offer_provider: OfferProvider | None = None,
    ) -> None:
        self._profile_provider = profile_provider or default_profile_provider()
        self._offer_provider = offer_provider or default_offer_provider()

    def profile(self, usage: CustomerUsage | Mapping[str, float]) -> ProfileResult:
        customer = _normalize_usage(usage)
        return self._profile_provider.profile(customer)

    def recommend(
        self,
        profile: ProfileResult | str,
        usage: CustomerUsage | Mapping[str, float],
    ) -> str:
        customer = _normalize_usage(usage)
        scoring = build_scoring_result(customer)
        if isinstance(profile, str):
            profile_result = ProfileResult(
                markdown=profile,
                usage=customer,
                scoring=scoring,
                source="external",
            )
        else:
            profile_result = ProfileResult(
                markdown=profile.markdown,
                usage=customer,
                scoring=scoring,
                source=profile.source,
                metadata=dict(profile.metadata),
            )
        return self._offer_provider.recommend(profile_result, customer)


_default_engine: ProfilerEngine | None = None


def get_engine() -> ProfilerEngine:
    """Return the process-wide default engine (lazy singleton)."""
    global _default_engine
    if _default_engine is None:
        _default_engine = ProfilerEngine()
    return _default_engine


def reset_engine() -> None:
    """Clear the singleton so providers are rebuilt (tests, env changes)."""
    global _default_engine
    _default_engine = None
