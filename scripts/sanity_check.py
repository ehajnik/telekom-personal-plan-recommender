#!/usr/bin/env python3
"""
End-to-end sanity checks for the Private Customer Profiler.

Run from project root:
    python scripts/sanity_check.py
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FAILURES: list[str] = []


def check(name: str, fn) -> None:
    try:
        fn()
        print(f"  OK  {name}")
    except Exception as exc:
        FAILURES.append(f"{name}: {exc}")
        print(f"  FAIL {name}: {exc}")
        traceback.print_exc()


def check_package_files() -> None:
    from telekom_profiler.paths import (
        ASSETS_DIR,
        DATA_DIR,
        PROMPT_TEMPLATES_DIR,
        THEME_DIR,
    )

    required = [
        ASSETS_DIR / "telekom-logo.svg",
        DATA_DIR / "consumer_archetypes.md",
        DATA_DIR / "plans_and_options.md",
        DATA_DIR / "tariffs_private.md",
        PROMPT_TEMPLATES_DIR / "run_profile.md",
        PROMPT_TEMPLATES_DIR / "run_offer.md",
        THEME_DIR / "app.css",
        THEME_DIR / "dt_theme.py",
    ]
    missing = [p for p in required if not p.is_file()]
    if missing:
        raise FileNotFoundError("Missing: " + ", ".join(str(p) for p in missing))


def check_imports() -> None:
    import telekom_profiler  # noqa: F401
    from telekom_profiler import create_demo, main  # noqa: F401
    from telekom_profiler.config.ollama_settings import llm_enabled

    assert callable(main)
    assert isinstance(llm_enabled(), bool)


def check_prompts() -> None:
    from telekom_profiler.prompts import build_offer_prompt, build_profile_prompt

    data = {
        "data_gb": 30.0,
        "voice_min": 400.0,
        "sms_count": 50.0,
        "roaming_days": 2.0,
        "data_trend": 5.0,
        "voice_trend": 0.0,
    }
    profile_prompt = build_profile_prompt(data)
    for token in (
        "{slider_features}",
        "{centroid_distances}",
        "{distance_table}",
        "{overlay_signals}",
        "{required_primary}",
        "{required_confidence}",
        "{metrics_block}",
    ):
        if token in profile_prompt:
            raise ValueError(f"Unfilled placeholder {token} in profile prompt")

    profile = "Test profile body"
    offer_prompt = build_offer_prompt(profile)
    for token in ("{customer_profile}", "{tariffs_and_options}", "{primary_profile}", "{overlay_signals}"):
        if token in offer_prompt:
            raise ValueError(f"Unfilled placeholder {token} in offer prompt")
    if profile not in offer_prompt:
        raise ValueError("Customer profile not injected into offer prompt")


def check_typed_models() -> None:
    import os
    from unittest.mock import patch

    from telekom_profiler.domain import CustomerUsage, build_scoring_result
    from telekom_profiler.services.analysis import profile_customer_structured

    os.environ["PROFILER_MODE"] = "rules"
    data = {
        "data_gb": 95.0,
        "voice_min": 200.0,
        "sms_count": 30.0,
        "roaming_days": 8.0,
        "data_trend": 15.0,
        "voice_trend": -5.0,
    }
    usage = CustomerUsage.from_mapping(data)
    scoring = build_scoring_result(usage)
    if scoring.primary_name != "Streamer":
        raise AssertionError(f"Expected Streamer, got {scoring.primary_name}")

    with patch("telekom_profiler.services.providers.llm_enabled", return_value=False):
        result = profile_customer_structured(data)
    if result.scoring is None or result.is_placeholder:
        raise AssertionError("Structured profile should include scoring and real markdown")


def check_domain_pipeline() -> None:
    from telekom_profiler.domain import (
        compute_archetype_distances,
        render_offer_report,
        render_profile_report,
    )

    data = {
        "data_gb": 95.0,
        "voice_min": 200.0,
        "sms_count": 30.0,
        "roaming_days": 8.0,
        "data_trend": 15.0,
        "voice_trend": -5.0,
    }
    primary, _ = compute_archetype_distances(data)[0]
    if primary != "Streamer":
        raise AssertionError(f"Expected Streamer, got {primary}")

    profile = render_profile_report(data)
    offer = render_offer_report(profile, data)
    for needle in ("Streamer", "MagentaMobil", "### 1."):
        if needle not in profile and needle not in offer:
            raise AssertionError(f"Expected {needle!r} in output")


def check_services_fallback() -> None:
    from unittest.mock import patch

    from telekom_profiler.services.analysis import profile_customer, recommend_offer

    data = {
        "data_gb": 10.0,
        "voice_min": 2200.0,
        "sms_count": 120.0,
        "roaming_days": 5.0,
        "data_trend": -5.0,
        "voice_trend": 10.0,
    }
    with patch("telekom_profiler.services.providers.llm_enabled", return_value=False):
        profile = profile_customer(data)
        offer = recommend_offer(profile, data)
    if "Chatterbox" not in profile:
        raise AssertionError("Chatterbox preset should map to Chatterbox archetype")
    if "MagentaMobil" not in offer:
        raise AssertionError("Offer should reference catalog tariff")


def check_theme_css() -> None:
    from telekom_profiler.ui.theme import DT_CSS, DT_THEME

    if len(DT_CSS) < 500:
        raise ValueError("DT_CSS unexpectedly short")
    if DT_THEME is None:
        raise ValueError("DT_THEME not loaded")


def check_demo_builds() -> None:
    from telekom_profiler import create_demo

    demo = create_demo()
    if demo.__class__.__name__ != "Blocks":
        raise TypeError(f"Expected Gradio Blocks, got {type(demo)}")


def check_ml_artifacts_optional() -> None:
    from telekom_profiler.config.profiler_settings import artifacts_available
    from telekom_profiler.paths import ARTIFACTS_DIR

    if not artifacts_available():
        print("    (ML artifacts absent — run generate + subscriber_profiling for ML UI)")
        return
    required = [
        ARTIFACTS_DIR / "kmeans.pkl",
        ARTIFACTS_DIR / "scaler.pkl",
        ARTIFACTS_DIR / "subscriber_cluster_map.csv",
    ]
    missing = [p for p in required if not p.is_file()]
    if missing:
        raise FileNotFoundError("Incomplete artifacts: " + ", ".join(str(p) for p in missing))


def check_entrypoint() -> None:
    app_path = ROOT / "app.py"
    code = app_path.read_text(encoding="utf-8")
    if "telekom_profiler" not in code:
        raise ValueError("app.py must delegate to telekom_profiler")


def main() -> int:
    print("Sanity check — telekom-personal-plan-recommender\n")
    checks = [
        ("Package data files", check_package_files),
        ("Imports & public API", check_imports),
        ("Prompt template fill", check_prompts),
        ("Typed domain models", check_typed_models),
        ("Domain pipeline", check_domain_pipeline),
        ("Services (LLM fallback)", check_services_fallback),
        ("Theme & CSS", check_theme_css),
        ("Gradio demo builds", check_demo_builds),
        ("ML artifacts (optional)", check_ml_artifacts_optional),
        ("app.py entrypoint", check_entrypoint),
    ]
    for name, fn in checks:
        check(name, fn)

    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)} check(s)):")
        for msg in FAILURES:
            print(f"  - {msg}")
        return 1

    print("All sanity checks passed.")
    try:
        import ollama  # noqa: F401

        print("(ollama package installed — run: ollama serve && ollama pull <model>)")
    except ImportError:
        print("(ollama not installed — pip install -r requirements.txt)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
