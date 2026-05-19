"""Gradio UI for the Private Customer Profiler."""

from __future__ import annotations

from dataclasses import replace

import gradio as gr

from telekom_profiler.config import (
    CUSTOM_PROFILE,
    MSG_AFTER_PROFILE,
    MSG_GENERATE_OFFER,
    MSG_RUN_PROFILE,
    MSG_RUN_PROFILE_FIRST,
    SLIDER_KEYS,
    TREND_SLIDERS,
    USAGE_SLIDERS,
    SliderSpec,
    profile_template_choices,
)
from telekom_profiler.config.ollama_settings import fallback_on_error, llm_enabled
from telekom_profiler.domain.models import CustomerUsage, ProfileResult
from telekom_profiler.logging_config import configure_logging
from telekom_profiler.paths import ASSETS_DIR
from telekom_profiler.runtime_context import subscriber_id_var
from telekom_profiler.services import get_engine, reset_engine
from telekom_profiler.services.analysis import profile_customer_structured
from telekom_profiler.ui.helpers import (
    format_error_markdown,
    format_scoring_summary,
    inference_mode_label,
)
from telekom_profiler.ui.theme import DT_CSS, DT_THEME


def _header_html() -> str:
    logo_svg = (ASSETS_DIR / "telekom-logo.svg").read_text(encoding="utf-8")
    return f"""
<div id="dt-header">
  <div class="dt-logo">{logo_svg}</div>
  <div class="dt-text">
    <h1>Private Customer Profiler</h1>
    <p>Telekom Mobile — Usage-Driven Campaign Intelligence</p>
  </div>
</div>
""".strip()


def _subscriber_choices() -> list[str]:
    try:
        from telekom_profiler.ml.inference import list_subscriber_ids

        return list_subscriber_ids()
    except Exception:
        return []


def _make_slider(spec: SliderSpec) -> gr.Slider:
    label, minimum, maximum, default = spec
    return gr.Slider(minimum, maximum, value=default, label=label, step=1)


def _slider_data(*values: float) -> CustomerUsage:
    return CustomerUsage.from_mapping(
        dict(zip(SLIDER_KEYS, values, strict=True)),
        clamp=True,
    )


def load_profile_preset(profile_name: str, *current_values: float) -> list[float]:
    import json

    from telekom_profiler.config.sliders import CUSTOM_PROFILE, PROFILES
    from telekom_profiler.paths import ARTIFACTS_DIR

    if profile_name == CUSTOM_PROFILE:
        return list(current_values)
    chars_path = ARTIFACTS_DIR / "profile_characteristics.json"
    if chars_path.is_file():
        try:
            from telekom_profiler.ml.profile_characteristics import (
                get_profile,
                load_profiles_document,
            )

            doc = load_profiles_document(json.loads(chars_path.read_text(encoding="utf-8")))
            preset = get_profile(doc, profile_name).get("slider_defaults")
            if preset:
                return [
                    float(preset.get(key, current))
                    for key, current in zip(SLIDER_KEYS, current_values)
                ]
        except (json.JSONDecodeError, OSError, TypeError):
            pass
    preset = PROFILES.get(profile_name)
    if preset is None:
        return list(current_values)
    return [float(preset.get(key, current)) for key, current in zip(SLIDER_KEYS, current_values)]


def load_subscriber(subscriber_id: str | None, *current_values: float) -> list[float]:
    if not subscriber_id:
        return list(current_values)
    try:
        from telekom_profiler.ml.inference import get_slider_defaults_for_subscriber

        defaults = get_slider_defaults_for_subscriber(subscriber_id)
        if not defaults:
            return list(current_values)
        return [float(defaults.get(key, current)) for key, current in zip(SLIDER_KEYS, current_values)]
    except Exception:
        return list(current_values)


def run_profile(
    subscriber_id: str | None,
    *values: float,
) -> tuple[str, str, dict | None, str]:
    usage = _slider_data(*values)
    token = None
    if subscriber_id:
        token = subscriber_id_var.set(subscriber_id)
    try:
        result = profile_customer_structured(usage.as_dict())
        if subscriber_id:
            result = replace(
                result,
                metadata={**result.metadata, "subscriber_id": subscriber_id},
            )
        return (
            result.markdown,
            MSG_AFTER_PROFILE,
            result.to_state_dict(),
            format_scoring_summary(result),
        )
    except RuntimeError as exc:
        if llm_enabled() and not fallback_on_error():
            return (
                format_error_markdown("Profile", exc),
                MSG_AFTER_PROFILE,
                None,
                format_scoring_summary(None),
            )
        raise
    finally:
        if token is not None:
            subscriber_id_var.reset(token)


def generate_offer(
    profile_state: dict | None,
    *values: float,
) -> str:
    profile = ProfileResult.from_state_dict(profile_state)
    if profile is None or profile.is_placeholder:
        return MSG_RUN_PROFILE_FIRST
    usage = _slider_data(*values)
    try:
        return get_engine().recommend(profile, usage)
    except RuntimeError as exc:
        if llm_enabled() and not fallback_on_error():
            return format_error_markdown("Offer", exc)
        raise


def create_demo() -> gr.Blocks:
    subs = _subscriber_choices()
    template_choices = profile_template_choices()

    with gr.Blocks(title="Private Customer Profiler", fill_width=True) as demo:
        profile_state = gr.State(value=None)

        with gr.Row(elem_classes=["dt-header-row"]):
            gr.HTML(
                _header_html(),
                elem_classes=["dt-header-block"],
                padding=False,
                container=False,
            )

        with gr.Row(elem_classes=["dt-action-bar"]):
            gr.Markdown(inference_mode_label(), elem_classes=["dt-inference-mode"])
            subscriber_pick = gr.Dropdown(
                choices=[""] + subs if subs else [""],
                value="",
                label="Subscriber (12-month panel)",
                allow_custom_value=False,
                info="Select a subscriber or adjust sliders manually.",
            )
            profile_pick = gr.Dropdown(
                choices=template_choices,
                value=CUSTOM_PROFILE,
                label="Profile template",
            )

        with gr.Row(elem_classes=["dt-sliders-row"]):
            with gr.Column(elem_classes=["dt-feature-col"]):
                gr.Markdown("### Usage features", elem_classes=["dt-section-title"])
                usage_inputs = [_make_slider(USAGE_SLIDERS[k]) for k in USAGE_SLIDERS]

            with gr.Column(elem_classes=["dt-feature-col"]):
                gr.Markdown(
                    "### Trends\n\n"
                    "Trajectory only — overlays and narrative; **not** used in K-Means clustering.",
                    elem_classes=["dt-section-title"],
                )
                trend_inputs = [_make_slider(TREND_SLIDERS[k]) for k in TREND_SLIDERS]

        all_inputs = usage_inputs + trend_inputs

        with gr.Row(elem_classes=["dt-btn-row"]):
            run_btn = gr.Button("Run profile", variant="primary")
            offer_btn = gr.Button("Generate offer", variant="secondary")

        gr.Markdown("## Results", elem_classes=["dt-results-heading"])

        scoring_out = gr.Markdown(
            format_scoring_summary(None),
            elem_classes=["dt-scoring-summary"],
        )

        with gr.Row(elem_classes=["dt-results-row"]):
            with gr.Column(elem_classes=["dt-result-col"], scale=1, min_width=0):
                gr.Markdown("### Profile", elem_classes=["dt-section-title"])
                profile_out = gr.Markdown(
                    MSG_RUN_PROFILE,
                    elem_classes=["dt-result-body"],
                    padding=False,
                )

            with gr.Column(elem_classes=["dt-result-col"], scale=1, min_width=0):
                gr.Markdown("### Offer", elem_classes=["dt-section-title"])
                offer_out = gr.Markdown(
                    MSG_GENERATE_OFFER,
                    elem_classes=["dt-result-body"],
                    padding=False,
                )

        subscriber_pick.change(
            load_subscriber,
            inputs=[subscriber_pick, *all_inputs],
            outputs=all_inputs,
        )
        profile_pick.change(
            load_profile_preset,
            inputs=[profile_pick, *all_inputs],
            outputs=all_inputs,
        )
        run_btn.click(
            run_profile,
            inputs=[subscriber_pick, *all_inputs],
            outputs=[profile_out, offer_out, profile_state, scoring_out],
            show_progress="full",
        )
        offer_btn.click(
            generate_offer,
            inputs=[profile_state, *all_inputs],
            outputs=offer_out,
            show_progress="full",
        )

    return demo


def main() -> None:
    configure_logging()
    reset_engine()
    create_demo().launch(theme=DT_THEME, css=DT_CSS)
