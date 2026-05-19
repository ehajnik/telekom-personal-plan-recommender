"""Concrete profile and offer providers (Ollama LLM and rule-based fallback)."""

from __future__ import annotations

from telekom_profiler.config.ollama_settings import fallback_on_error, llm_enabled
from telekom_profiler.domain.models import CustomerUsage, ProfileResult
from telekom_profiler.domain.offers import render_offer_report
from telekom_profiler.domain.profiling import render_profile_report
from telekom_profiler.domain.scoring import build_scoring_result
from telekom_profiler.llm.client import chat_completion
from telekom_profiler.prompts.builder import build_offer_prompt, build_profile_prompt
from telekom_profiler.services.fallback import FallbackOfferProvider, FallbackProfileProvider
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
        markdown = chat_completion(build_profile_prompt(usage.as_dict()))
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
        return chat_completion(build_offer_prompt(profile.markdown))


def default_profile_provider() -> ProfileProvider:
    """Factory: Ollama (optionally wrapped) when enabled, otherwise rule-based."""
    rules = RuleBasedProfileProvider()
    if not llm_enabled():
        return rules
    ollama = OllamaProfileProvider()
    if fallback_on_error():
        return FallbackProfileProvider(ollama, rules)
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
