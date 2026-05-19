"""UI formatting helpers (no Gradio dependency)."""

from __future__ import annotations

from telekom_profiler.config.ollama_settings import (
    OLLAMA_FALLBACK_ON_ERROR,
    OLLAMA_MODEL,
    llm_enabled,
)
from telekom_profiler.config.profiler_settings import effective_profiler_mode
from telekom_profiler.domain.models import ProfileResult


def inference_mode_label() -> str:
    mode = effective_profiler_mode()
    base = f"Segmentation: **{mode}**"
    if mode == "ml":
        base += " (K-Means artifacts)"
    if not llm_enabled():
        return f"{base} · Inference: **rule-based** (Ollama disabled)"
    fallback = "with rule-based fallback" if OLLAMA_FALLBACK_ON_ERROR else "no fallback"
    return f"{base} · Inference: **Ollama** (`{OLLAMA_MODEL}`, {fallback})"


def format_scoring_summary(profile: ProfileResult | None) -> str:
    if profile is None or profile.is_placeholder:
        return "_Run **Run profile** to see profile scoring._"
    scoring = profile.scoring
    if scoring is None:
        return f"_Profile source: **{profile.source}** (no scoring metadata)._"

    overlays = (
        "\n".join(f"- {o}" for o in scoring.overlays)
        if scoring.overlays
        else "- None active"
    )
    secondary = (
        f"**{scoring.secondary.name}** ({scoring.secondary.distance:.3f})"
        if scoring.secondary
        else "—"
    )
    primary_line = (
        f"**Primary:** {scoring.primary.name} ({scoring.primary.distance:.3f}) · "
        f"**Confidence:** {scoring.confidence}"
    )

    distance_rows = ""
    if scoring.all_distances:
        distance_rows = "\n".join(
            f"| {s.name} | {s.distance:.3f} |" for s in scoring.all_distances
        )
        distance_block = f"""
**Distance table**

| Profile | Distance |
|---------|----------|
{distance_rows}
"""
    else:
        distance_block = ""

    sid = profile.metadata.get("subscriber_id")
    sid_line = f"\n**Subscriber:** `{sid}`" if sid else ""

    return f"""{primary_line}{sid_line}

**Secondary:** {secondary}
{distance_block}
**Overlays:**
{overlays}

**Source:** {profile.source}"""


def format_error_markdown(operation: str, error: Exception) -> str:
    return (
        f"### {operation} failed\n\n"
        f"Could not complete this step: {error}\n\n"
        "Check Ollama is running, the model is pulled, or set `OLLAMA_ENABLED=false` "
        "or `OLLAMA_FALLBACK_ON_ERROR=true` in `.env`. "
        "For ML mode, run `python scripts/generate_synthetic_data.py` and "
        "`python scripts/subscriber_profiling.py` first."
    )
