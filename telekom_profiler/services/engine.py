"""
Profiler engine — orchestrates profile and offer providers.

Use ``ProfilerEngine`` in services, notebooks, or batch jobs. Inject custom
``ProfileProvider`` / ``OfferProvider`` implementations for integration tests
or production backends.
"""

from __future__ import annotations

from typing import Mapping

from telekom_profiler.domain.models import CustomerUsage, ProfileResult
from telekom_profiler.services.protocols import OfferProvider, ProfileProvider
from telekom_profiler.services.providers import (
    default_offer_provider,
    default_profile_provider,
)


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
        customer = (
            usage if isinstance(usage, CustomerUsage) else CustomerUsage.from_mapping(usage)
        )
        return self._profile_provider.profile(customer)

    def recommend(
        self,
        profile: ProfileResult | str,
        usage: CustomerUsage | Mapping[str, float],
    ) -> str:
        if isinstance(profile, str):
            customer = (
                usage
                if isinstance(usage, CustomerUsage)
                else CustomerUsage.from_mapping(usage)
            )
            profile_result = ProfileResult(
                markdown=profile,
                usage=customer,
                source="external",
            )
        else:
            profile_result = profile
            customer = (
                usage
                if isinstance(usage, CustomerUsage)
                else CustomerUsage.from_mapping(usage)
            )
        return self._offer_provider.recommend(profile_result, customer)


_default_engine: ProfilerEngine | None = None


def get_engine() -> ProfilerEngine:
    """Return the process-wide default engine (lazy singleton)."""
    global _default_engine
    if _default_engine is None:
        _default_engine = ProfilerEngine()
    return _default_engine
