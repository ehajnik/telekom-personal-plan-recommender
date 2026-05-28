"""Providers that fall back to rule-based logic when the primary provider fails."""

from __future__ import annotations

import logging

from telekom_profiler.domain.models import CustomerUsage, ProfileResult
from telekom_profiler.services.protocols import OfferProvider, ProfileProvider

_logger = logging.getLogger(__name__)


class FallbackProfileProvider:
    """Try primary (e.g. Ollama); on failure delegate to fallback rules."""

    source = "fallback"

    def __init__(
        self,
        primary: ProfileProvider,
        fallback: ProfileProvider,
    ) -> None:
        self._primary = primary
        self._fallback = fallback

    def profile(self, usage: CustomerUsage) -> ProfileResult:
        try:
            result = self._primary.profile(usage)
            return ProfileResult(
                markdown=result.markdown,
                usage=result.usage,
                scoring=result.scoring,
                source=result.source,
                metadata=dict(result.metadata),
            )
        except RuntimeError as exc:
            _logger.warning("Profile primary failed, using rule-based fallback: %s", exc)
            fb = self._fallback.profile(usage)
            metadata = dict(fb.metadata)
            metadata["fallback_reason"] = str(exc)
            metadata["primary_source"] = getattr(self._primary, "source", "unknown")
            return ProfileResult(
                markdown=fb.markdown,
                usage=fb.usage,
                scoring=fb.scoring,
                source="rule_based_fallback",
                metadata=metadata,
            )


class FallbackOfferProvider:
    """Try primary (e.g. Ollama); on failure delegate to rule-based offer."""

    source = "fallback"

    def __init__(
        self,
        primary: OfferProvider,
        fallback: OfferProvider,
    ) -> None:
        self._primary = primary
        self._fallback = fallback

    def recommend(self, profile: ProfileResult, usage: CustomerUsage) -> str:
        try:
            return self._primary.recommend(profile, usage)
        except RuntimeError as exc:
            _logger.warning("Offer primary failed, using rule-based fallback: %s", exc)
            fallback_offer = self._fallback.recommend(profile, usage)
            return (
                "### Offer fallback applied\n\n"
                "LLM offer generation failed, so a rule-based offer was generated instead.\n\n"
                f"Reason: `{exc}`\n\n"
                f"{fallback_offer}"
            )
