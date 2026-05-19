"""
Private Customer Profiler — Gradio UI for Telekom usage-driven plan recommendations.

Placeholder business logic builds a markdown profile from sliders and a sample offer.
Replace ``run_profile`` and ``generate_offer`` with your clustering / rules engine / LLM.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import gradio as gr

from styles.dt_theme import DT_CSS, DT_THEME

# ── Paths & copy ─────────────────────────────────────────────────────────────

ROOT: Final[Path] = Path(__file__).resolve().parent
ASSETS: Final[Path] = ROOT / "assets"

CUSTOM_PROFILE: Final[str] = "— Custom —"
PLACEHOLDER_PREFIX: Final[str] = "_"

MSG_RUN_PROFILE: Final[str] = "_Run the profile to see analysis here._"
MSG_AFTER_PROFILE: Final[str] = "_Click **Generate offer** after running the profile._"
MSG_RUN_PROFILE_FIRST: Final[str] = "_Run the profile first, then generate an offer._"
MSG_GENERATE_OFFER: Final[str] = "_Generate an offer after profiling._"

# ── Slider definitions: key -> (label, min, max, default) ───────────────────

SliderSpec = tuple[str, int, int, int]

USAGE_SLIDERS: Final[dict[str, SliderSpec]] = {
    "data_gb": ("Monthly data (GB)", 0, 150, 30),
    "voice_min": ("Voice minutes", 0, 3000, 400),
    "sms_count": ("SMS count", 0, 500, 50),
    "roaming_days": ("Roaming days / month", 0, 30, 2),
}

TREND_SLIDERS: Final[dict[str, SliderSpec]] = {
    "data_trend": ("Data trend", -50, 50, 5),
    "voice_trend": ("Voice trend", -50, 50, 0),
}

SLIDER_KEYS: Final[tuple[str, ...]] = tuple(USAGE_SLIDERS) + tuple(TREND_SLIDERS)

ProfilePreset = dict[str, int] | None

PROFILES: Final[dict[str, ProfilePreset]] = {
    CUSTOM_PROFILE: None,
    "Heavy data user": {
        "data_gb": 95,
        "voice_min": 200,
        "sms_count": 30,
        "roaming_days": 8,
        "data_trend": 15,
        "voice_trend": -5,
    },
    "Voice-first business": {
        "data_gb": 10,
        "voice_min": 2200,
        "sms_count": 120,
        "roaming_days": 5,
        "data_trend": -5,
        "voice_trend": 10,
    },
}


def _header_html() -> str:
    logo_svg = (ASSETS / "telekom-logo.svg").read_text(encoding="utf-8")
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


def make_slider(spec: SliderSpec) -> gr.Slider:
    label, minimum, maximum, default = spec
    return gr.Slider(minimum, maximum, value=default, label=label, step=1)


def load_profile(profile_name: str, *current_values: float) -> list[float]:
    """Apply a template preset to sliders, or keep current values for custom."""
    preset = PROFILES.get(profile_name)
    if preset is None:
        return list(current_values)
    return [preset.get(key, current) for key, current in zip(SLIDER_KEYS, current_values)]


def run_profile(*values: float) -> tuple[str, str]:
    """Build a short profile summary from slider values (placeholder logic)."""
    data = dict(zip(SLIDER_KEYS, values, strict=True))

    profile = f"""### Customer snapshot

| Metric | Value |
|--------|------:|
| Data | {data["data_gb"]:.0f} GB |
| Voice | {data["voice_min"]:.0f} min |
| SMS | {data["sms_count"]:.0f} |
| Roaming | {data["roaming_days"]:.0f} days |

**Trends:** data {data["data_trend"]:+.0f}, voice {data["voice_trend"]:+.0f}  
*(Trends describe trajectory; they do not change cluster assignment.)*
"""
    return profile, MSG_AFTER_PROFILE


def generate_offer(profile_text: str) -> str:
    """Produce a tariff recommendation from the profile markdown (placeholder)."""
    if _is_placeholder(profile_text):
        return MSG_RUN_PROFILE_FIRST
    return """### Suggested offer

- **Tariff:** Business Mobile L (unlimited EU data bucket)
- **Add-on:** Roaming Plus (matches elevated roaming days)
- **Note:** Placeholder recommendation — connect your rules engine or LLM here.
"""


def create_demo() -> gr.Blocks:
    """Build the Gradio Blocks app (layout + event wiring)."""
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

        with gr.Row():
            with gr.Column(elem_classes=["dt-feature-col"]):
                gr.Markdown("### Usage features", elem_classes=["dt-subtitle"])
                usage_inputs = [make_slider(USAGE_SLIDERS[k]) for k in USAGE_SLIDERS]

            with gr.Column(elem_classes=["dt-feature-col"]):
                gr.Markdown(
                    "### Trends\n\n"
                    "Trajectory only — tags growth/decline, not cluster assignment.",
                    elem_classes=["dt-subtitle"],
                )
                trend_inputs = [make_slider(TREND_SLIDERS[k]) for k in TREND_SLIDERS]

        all_inputs = usage_inputs + trend_inputs

        with gr.Row(elem_classes=["dt-btn-row"]):
            with gr.Column(elem_classes=["dt-feature-col"]):
                run_btn = gr.Button("Run profile", variant="primary")
            with gr.Column(elem_classes=["dt-feature-col"]):
                offer_btn = gr.Button("Generate offer", variant="secondary")

        gr.Markdown("## Results")
        gr.Markdown("### Profile")
        profile_out = gr.Markdown(MSG_RUN_PROFILE)
        gr.Markdown("### Offer")
        offer_out = gr.Markdown(MSG_GENERATE_OFFER)

        profile_pick.change(
            load_profile,
            inputs=[profile_pick, *all_inputs],
            outputs=all_inputs,
        )
        run_btn.click(run_profile, inputs=all_inputs, outputs=[profile_out, offer_out])
        offer_btn.click(generate_offer, inputs=profile_out, outputs=offer_out)

    return demo


def main() -> None:
    demo = create_demo()
    demo.launch(theme=DT_THEME, css=DT_CSS)


if __name__ == "__main__":
    main()
