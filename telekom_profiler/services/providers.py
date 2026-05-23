"""Concrete profile and offer providers (Ollama LLM and rule-based fallback)."""

from __future__ import annotations

from telekom_profiler.config.ollama_settings import fallback_on_error, llm_enabled
from telekom_profiler.config.profiler_settings import effective_profiler_mode
from telekom_profiler.domain.models import CustomerUsage, ProfileResult
from telekom_profiler.domain.offers import render_offer_report
from telekom_profiler.domain.profiling import render_profile_report
from telekom_profiler.domain.scoring import build_scoring_result
from telekom_profiler.llm.client import chat_completion
from telekom_profiler.prompts.builder import (
    build_offer_prompt,
    build_profile_prompt,
    format_distance_table,
)
from telekom_profiler.services.fallback import FallbackOfferProvider, FallbackProfileProvider
from telekom_profiler.services.ml_profile_provider import MlProfileProvider
from telekom_profiler.services.protocols import OfferProvider, ProfileProvider


class RuleBasedProfileProvider:
    """Deterministic profile from archetype math and template sections."""

    source = "rule_based"

    def profile(self, usage: CustomerUsage) -> ProfileResult:
        scoring = build_scoring_result(usage)
        markdown = render_profile_report(usage.as_dict())
        return ProfileResult(
            markdown=markdown,
            usage=usage,
            scoring=scoring,
            source=self.source,
        )


class OllamaProfileProvider:
    """Profile via local Ollama; scoring metadata still computed deterministically."""

    source = "ollama"

    def profile(self, usage: CustomerUsage) -> ProfileResult:
        scoring = build_scoring_result(usage)
        metrics_block = format_distance_table(scoring) if scoring.all_distances else ""
        markdown = chat_completion(
            build_profile_prompt(usage.as_dict(), metrics_block=metrics_block)
        )
        return ProfileResult(
            markdown=markdown,
            usage=usage,
            scoring=scoring,
            source=self.source,
        )


class RuleBasedOfferProvider:
    """Deterministic offer from usage thresholds and prototype catalog."""

    source = "rule_based"

    def recommend(self, profile: ProfileResult, usage: CustomerUsage) -> str:
        return render_offer_report(
            profile.markdown,
            usage.as_dict(),
            scoring=profile.scoring,
        )


class OllamaOfferProvider:
    """Offer via local Ollama using profile markdown and tariff reference data."""

    source = "ollama"

    def recommend(self, profile: ProfileResult, usage: CustomerUsage) -> str:
        return chat_completion(build_offer_prompt(profile.markdown, scoring=profile.scoring))


def _base_profile_provider() -> ProfileProvider:
    """Rule-based or ML segmentation (no LLM)."""
    if effective_profiler_mode() == "ml":
        return MlProfileProvider()
    return RuleBasedProfileProvider()


def _profile_fallback_provider() -> ProfileProvider:
    """Deterministic fallback when Ollama fails (matches active profiler mode)."""
    if effective_profiler_mode() == "ml":
        return MlProfileProvider()
    return RuleBasedProfileProvider()


def default_profile_provider() -> ProfileProvider:
    """Factory: ML or rules base; Ollama wraps when enabled."""
    base = _base_profile_provider()
    if not llm_enabled():
        return base
    ollama = OllamaProfileProvider()
    if fallback_on_error():
        return FallbackProfileProvider(ollama, _profile_fallback_provider())
    return ollama


def default_offer_provider() -> OfferProvider:
    """Factory: Ollama (optionally wrapped) when enabled, otherwise rule-based."""
    rules = RuleBasedOfferProvider()
    if not llm_enabled():
        return rules
    ollama = OllamaOfferProvider()
    if fallback_on_error():
        return FallbackOfferProvider(ollama, rules)
    return ollama
