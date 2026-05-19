"""Application services — profiling and offer orchestration."""

from telekom_profiler.services.analysis import (
    profile_customer,
    profile_customer_structured,
    recommend_offer,
)
from telekom_profiler.services.engine import ProfilerEngine, get_engine
from telekom_profiler.services.protocols import OfferProvider, ProfileProvider

__all__ = [
    "OfferProvider",
    "ProfilerEngine",
    "ProfileProvider",
    "get_engine",
    "profile_customer",
    "profile_customer_structured",
    "recommend_offer",
]
