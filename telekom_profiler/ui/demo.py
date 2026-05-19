"""Gradio UI for the Private Customer Profiler."""

from __future__ import annotations

import gradio as gr

from telekom_profiler.config import (
    CUSTOM_PROFILE,
    MSG_AFTER_PROFILE,
    MSG_GENERATE_OFFER,
    MSG_RUN_PROFILE,
    MSG_RUN_PROFILE_FIRST,
    PLACEHOLDER_PREFIX,
    PROFILES,
    SLIDER_KEYS,
    TREND_SLIDERS,
    USAGE_SLIDERS,
    SliderSpec,
)
from telekom_profiler.paths import ASSETS_DIR
from telekom_profiler.services import profile_customer, recommend_offer
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


def _is_placeholder(text: str) -> bool:
    return not text.strip() or text.startswith(PLACEHOLDER_PREFIX)


def _make_slider(spec: SliderSpec) -> gr.Slider:
    label, minimum, maximum, default = spec
    return gr.Slider(minimum, maximum, value=default, label=label, step=1)


def _slider_data(*values: float) -> dict[str, float]:
    return dict(zip(SLIDER_KEYS, values, strict=True))


def load_profile_preset(profile_name: str, *current_values: float) -> list[float]:
    preset = PROFILES.get(profile_name)
    if preset is None:
        return list(current_values)
    return [preset.get(key, current) for key, current in zip(SLIDER_KEYS, current_values)]


def run_profile(*values: float) -> tuple[str, str]:
    return profile_customer(_slider_data(*values)), MSG_AFTER_PROFILE


def generate_offer(profile_text: str, *values: float) -> str:
    if _is_placeholder(profile_text):
        return MSG_RUN_PROFILE_FIRST
    return recommend_offer(profile_text, _slider_data(*values))


def create_demo() -> gr.Blocks:
    with gr.Blocks(title="Private Customer Profiler") as demo:
        with gr.Row(elem_classes=["dt-header-row"]):
            gr.HTML(
                _header_html(),
                elem_classes=["dt-header-block"],
                padding=False,
                container=False,
            )

        with gr.Row(elem_classes=["dt-action-bar"]):
            profile_pick = gr.Dropdown(
                choices=list(PROFILES),
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
                    "Trajectory only — tags growth/decline, not cluster assignment.",
                    elem_classes=["dt-section-title"],
                )
                trend_inputs = [_make_slider(TREND_SLIDERS[k]) for k in TREND_SLIDERS]

        all_inputs = usage_inputs + trend_inputs

        with gr.Row(elem_classes=["dt-btn-row"]):
            run_btn = gr.Button("Run profile", variant="primary")
            offer_btn = gr.Button("Generate offer", variant="secondary")

        gr.Markdown("## Results", elem_classes=["dt-results-heading"])

        with gr.Row(elem_classes=["dt-results-row"]):
            with gr.Column(elem_classes=["dt-result-col"]):
                gr.Markdown("### Profile", elem_classes=["dt-section-title"])
                profile_out = gr.Markdown(MSG_RUN_PROFILE, elem_classes=["dt-result-body"])

            with gr.Column(elem_classes=["dt-result-col"]):
                gr.Markdown("### Offer", elem_classes=["dt-section-title"])
                offer_out = gr.Markdown(MSG_GENERATE_OFFER, elem_classes=["dt-result-body"])

        profile_pick.change(
            load_profile_preset,
            inputs=[profile_pick, *all_inputs],
            outputs=all_inputs,
        )
        run_btn.click(run_profile, inputs=all_inputs, outputs=[profile_out, offer_out])
        offer_btn.click(
            generate_offer,
            inputs=[profile_out, *all_inputs],
            outputs=offer_out,
        )

    return demo


def main() -> None:
    create_demo().launch(theme=DT_THEME, css=DT_CSS)
