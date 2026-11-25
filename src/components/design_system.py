"""Reusable visual primitives for the Concept Match Flet UI."""

import flet as ft

from theme import colors, typography
from theme.styles import card_style, danger_button, ghost_button, primary_button, secondary_button


def text(value: str, size: int = typography.BODY, *, color: str = colors.INK, weight=None, max_lines=None, text_align=None) -> ft.Text:
    return ft.Text(value, size=size, color=color, weight=weight, font_family=typography.FONT_FAMILY, max_lines=max_lines, text_align=text_align)


def button(label: str, on_click, *, kind: str = "primary", dark: bool = False) -> ft.Control:
    style = ghost_button() if dark and kind != "danger" else danger_button() if kind == "danger" else primary_button() if kind == "primary" else secondary_button()
    return ft.FilledButton(label, on_click=on_click, style=style, height=46)


def surface(content: ft.Control, *, fill: str = colors.WHITE, padding=18, radius: int = 18, expand=False) -> ft.Container:
    return ft.Container(content, padding=padding, expand=expand, **card_style(fill=fill, radius=radius))


def eyebrow(label: str, *, color: str = colors.GREEN_ACCENT) -> ft.Text:
    return text(label.upper(), typography.LABEL, color=color, weight=ft.FontWeight.W_700)


def stat_card(label: str, value: str, *, accent: str = colors.GREEN_ACCENT) -> ft.Container:
    return surface(ft.Column([eyebrow(label, color=accent), text(value, 22, weight=ft.FontWeight.W_700)], spacing=6), padding=14, radius=16, expand=True)


def badge(label: str, *, fill: str = colors.GREEN_LIGHT, color: str = colors.HOUSE_GREEN) -> ft.Container:
    return ft.Container(text(label, typography.MICRO, color=color, weight=ft.FontWeight.W_700), bgcolor=fill, border_radius=20, padding=ft.Padding.symmetric(horizontal=10, vertical=6))


def section_title(title: str, subtitle: str | None = None) -> ft.Column:
    children = [text(title, typography.SECTION, color=colors.HOUSE_GREEN, weight=ft.FontWeight.W_700)]
    if subtitle:
        children.append(text(subtitle, typography.CAPTION, color=colors.INK_LIGHT))
    return ft.Column(children, spacing=4)


def hero_visual(content: ft.Control, *, height: int = 250, fill: str = colors.GREEN_UPLIFT, padding: int = 18) -> ft.Container:
    return ft.Container(content, height=height, bgcolor=fill, border_radius=22, padding=padding, alignment=ft.Alignment(0, 0), clip_behavior=ft.ClipBehavior.HARD_EDGE)


def concept_node(icon: ft.IconData, *, size: int = 64, fill: str = colors.WHITE, color: str = colors.HOUSE_GREEN) -> ft.Container:
    return ft.Container(ft.Icon(icon, size=size * 0.48, color=color), width=size, height=size, bgcolor=fill, border_radius=size / 2, alignment=ft.Alignment(0, 0), shadow=ft.BoxShadow(blur_radius=8, color=colors.SHADOW, offset=ft.Offset(0, 3)))


def illustration_card(title: str, body: str, *, fill: str = colors.QUESTION_SURFACE, accent: str = colors.GOLD, width: int = 130, height: int = 92) -> ft.Container:
    return ft.Container(ft.Column([text(title, typography.LABEL, color=accent, weight=ft.FontWeight.W_700), text(body, 14, color=colors.INK, weight=ft.FontWeight.W_700, max_lines=3)], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6), width=width, height=height, bgcolor=fill, border=ft.Border.all(1, "#d8cfc2"), border_radius=14, padding=10, rotate=0.02, shadow=ft.BoxShadow(blur_radius=8, color=colors.SHADOW, offset=ft.Offset(0, 3)))


def progress_ring(value: float, label: str, *, size: int = 152) -> ft.Container:
    ring = ft.ProgressRing(value=max(0.0, min(1.0, value)), color=colors.GOLD, bgcolor="#487266", stroke_width=10, width=size, height=size)
    return ft.Container(ft.Stack([ring, ft.Column([text(label, 28, color=colors.WHITE, weight=ft.FontWeight.W_700), text("Completed", 12, color="#d9e8e2")], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)], alignment=ft.Alignment(0, 0)), width=size, height=size)


def pager_title_block(title: str, description: str) -> ft.Column:
    return ft.Column([text(title, 30, color=colors.WHITE, weight=ft.FontWeight.W_700), text(description, 15, color="#d9e8e2", max_lines=2)], spacing=8)


def combo_badge(combo: int) -> ft.Container:
    """Live streak chip.

    The fill steps from calm mint to gold to alert red as the chain grows, so
    the HUD itself reports how hot the run is. ``animate_scale`` is declared
    here so App.pulse_combo() only has to change ``scale`` twice to get a pop.
    """
    if combo <= 0:
        fill, ink = colors.GREEN_LIGHT, colors.HOUSE_GREEN
    elif combo < 3:
        fill, ink = colors.GOLD, colors.HOUSE_GREEN
    else:
        # Hot streak: highest contrast the palette offers, still legible.
        fill, ink = colors.ERROR, colors.WHITE
    return ft.Container(
        text(f"Chain ×{combo}", typography.MICRO, color=ink, weight=ft.FontWeight.W_700),
        bgcolor=fill,
        border_radius=20,
        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
        animate_scale=ft.Animation(170, ft.AnimationCurve.EASE_OUT_BACK),
        scale=ft.Scale(1.0),
    )
