"""Deutsche Telekom Magenta Gradio theme (light + dark)."""


import gradio as gr

from telekom_profiler.paths import THEME_DIR

MAGENTA = "#E20074"
MAGENTA_HOVER = "#C0005F"
MAGENTA_LIGHT = "#F48BBF"
DARK = "#191919"
DARK_SURFACE = "#262626"
DARK_BORDER = "#404040"
WHITE = "#FFFFFF"
PAGE_BG = "#EBEBED"
INSET_BG = "#EBEBED"
TEXT = "#191919"
TEXT_MUTED = "#737373"
BORDER = "#D8D8DC"

DT_MAGENTA = gr.themes.Color(
    c50="#fce4f2",
    c100="#f9b8dc",
    c200="#f48bbf",
    c300="#ef5ea3",
    c400="#eb3d91",
    c500="#e20074",
    c600="#c90068",
    c700="#b00059",
    c800="#97004b",
    c900="#7e003d",
    c950="#650030",
)

DT_CSS = (THEME_DIR / "app.css").read_text(encoding="utf-8")

DT_THEME = (
    gr.themes.Base(
        primary_hue=DT_MAGENTA,
        neutral_hue=gr.themes.colors.gray,
        font=(
            gr.themes.GoogleFont("Helvetica Neue"),
            "Arial",
            "sans-serif",
        ),
    )
    .set(
        body_background_fill=PAGE_BG,
        body_text_color=TEXT,
        body_text_color_subdued=TEXT_MUTED,
        background_fill_primary=WHITE,
        background_fill_secondary=INSET_BG,
        block_background_fill=WHITE,
        block_border_color=BORDER,
        border_color_primary=BORDER,
        input_background_fill=INSET_BG,
        input_border_color=BORDER,
        color_accent=MAGENTA,
        link_text_color=MAGENTA,
        slider_color=MAGENTA,
        button_primary_background_fill=MAGENTA,
        button_primary_background_fill_hover=MAGENTA_HOVER,
        button_primary_border_color=MAGENTA,
        button_primary_border_color_hover=MAGENTA_HOVER,
        button_primary_text_color=WHITE,
        button_secondary_background_fill=WHITE,
        button_secondary_background_fill_hover="#FDF0F7",
        button_secondary_border_color=MAGENTA,
        button_secondary_border_color_hover=MAGENTA,
        button_secondary_text_color=MAGENTA,
        table_border_color=BORDER,
        table_even_background_fill=WHITE,
        table_odd_background_fill=INSET_BG,
        body_background_fill_dark=DARK,
        body_text_color_dark="#E8E8E8",
        body_text_color_subdued_dark=TEXT_MUTED,
        background_fill_primary_dark=DARK_SURFACE,
        background_fill_secondary_dark="#2E2E2E",
        block_background_fill_dark=DARK_SURFACE,
        block_border_color_dark=DARK_BORDER,
        border_color_primary_dark=DARK_BORDER,
        input_background_fill_dark="#2E2E2E",
        input_border_color_dark=DARK_BORDER,
        link_text_color_dark=MAGENTA_LIGHT,
        slider_color_dark=MAGENTA,
        button_primary_background_fill_dark=MAGENTA,
        button_primary_background_fill_hover_dark=MAGENTA_HOVER,
        button_primary_text_color_dark=WHITE,
        button_secondary_background_fill_dark=DARK_SURFACE,
        button_secondary_background_fill_hover_dark="#3D1529",
        button_secondary_border_color_dark=MAGENTA,
        button_secondary_text_color_dark=MAGENTA_LIGHT,
        table_border_color_dark=DARK_BORDER,
        table_even_background_fill_dark=DARK_SURFACE,
        table_odd_background_fill_dark=DARK,
    )
)

__all__ = ["DT_CSS", "DT_THEME"]
