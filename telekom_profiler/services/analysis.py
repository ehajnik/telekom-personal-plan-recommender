"""Orchestrate Ollama prompts with rule-based fallback when Ollama is disabled."""

from __future__ import annotations

from telekom_profiler.config.ollama_settings import llm_enabled
from telekom_profiler.domain.offers import render_offer_report
from telekom_profiler.domain.profiling import render_profile_report
from telekom_profiler.llm.client import chat_completion
from telekom_profiler.prompts.builder import build_offer_prompt, build_profile_prompt


def profile_customer(data: dict[str, float]) -> str:
    if llm_enabled():
        return chat_completion(build_profile_prompt(data))
    return render_profile_report(data)


def recommend_offer(profile_text: str, data: dict[str, float]) -> str:
    if llm_enabled():
        return chat_completion(build_offer_prompt(profile_text))
    return render_offer_report(profile_text, data)
