"""Concrete profile and offer providers (LiteLLM and rule-based fallback)."""

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

PROFILE_HEADINGS: tuple[str, ...] = (
    "### 1. Primary archetype",
    "### 2. Overlay characteristics",
    "### 3. Secondary archetype influence",
    "### 4. Lifestyle narrative",
    "### 5. Likely customer context",
    "### 6. Pain points & risks",
    "### 7. Upsell & retention signals",
)

OFFER_HEADINGS: tuple[str, ...] = (
    "### 1. Recommended main tariff",
    "### 2. Recommended add-ons and options",
    "### 3. Contract and channel notes",
    "### 4. Indicative pricing",
    "### 5. Important caveats",
    "### 6. Next steps for the agent",
)

END_MARKER = "[END_OF_REPORT]"


def _strip_end_marker(markdown: str) -> str:
    return markdown.replace(END_MARKER, "").strip()


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


class LiteLLMProfileProvider:
    """Profile via LiteLLM; scoring metadata still computed deterministically."""

    source = "ollama"

    def profile(self, usage: CustomerUsage) -> ProfileResult:
        scoring = build_scoring_result(usage)
        metrics_block = format_distance_table(scoring) if scoring.all_distances else ""
        markdown = chat_completion(
            build_profile_prompt(usage.as_dict(), metrics_block=metrics_block),
            required_headings=PROFILE_HEADINGS,
            required_tail=END_MARKER,
        )
        markdown = _strip_end_marker(markdown)
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


class LiteLLMOfferProvider:
    """Offer via LiteLLM using profile markdown and tariff reference data."""

    source = "ollama"

    def recommend(self, profile: ProfileResult, usage: CustomerUsage) -> str:
        markdown = chat_completion(
            build_offer_prompt(profile.markdown, scoring=profile.scoring),
            required_headings=OFFER_HEADINGS,
            required_tail=END_MARKER,
        )
        return _strip_end_marker(markdown)


def _base_profile_provider() -> ProfileProvider:
    """Rule-based or ML segmentation (no LLM)."""
    if effective_profiler_mode() == "ml":
        return MlProfileProvider()
    return RuleBasedProfileProvider()


def _profile_fallback_provider() -> ProfileProvider:
    """Deterministic fallback when LLM fails (matches active profiler mode)."""
    if effective_profiler_mode() == "ml":
        return MlProfileProvider()
    return RuleBasedProfileProvider()


def default_profile_provider() -> ProfileProvider:
    """Factory: ML or rules base; LiteLLM wraps when enabled."""
    base = _base_profile_provider()
    if not llm_enabled():
        return base
    llm = LiteLLMProfileProvider()
    if fallback_on_error():
        return FallbackProfileProvider(llm, _profile_fallback_provider())
    return llm


def default_offer_provider() -> OfferProvider:
    """Factory: LiteLLM (optionally wrapped) when enabled, otherwise rule-based."""
    rules = RuleBasedOfferProvider()
    if not llm_enabled():
        return rules
    llm = LiteLLMOfferProvider()
    if fallback_on_error():
        return FallbackOfferProvider(llm, rules)
    return llm


# Backward-compatible aliases used in legacy tests/imports.
OllamaProfileProvider = LiteLLMProfileProvider
OllamaOfferProvider = LiteLLMOfferProvider
