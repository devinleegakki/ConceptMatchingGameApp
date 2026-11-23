import flet as ft

from theme import colors


def pill_style(bg: str, fg: str, border: str | None = None) -> ft.ButtonStyle:
    return ft.ButtonStyle(
        bgcolor=bg,
        color=fg,
        padding=ft.Padding.symmetric(horizontal=22, vertical=11),
        shape=ft.RoundedRectangleBorder(radius=50),
        side=ft.BorderSide(1, border or bg),
        animation_duration=200,
    )


def primary_button() -> ft.ButtonStyle:
    return pill_style(colors.GREEN_ACCENT, colors.WHITE)


def secondary_button() -> ft.ButtonStyle:
    return pill_style("transparent", colors.GREEN_ACCENT, colors.GREEN_ACCENT)


def dark_button() -> ft.ButtonStyle:
    return pill_style(colors.BLACK, colors.WHITE)


def ghost_button() -> ft.ButtonStyle:
    return pill_style("transparent", colors.WHITE, "#6a8f81")


def danger_button() -> ft.ButtonStyle:
    return pill_style(colors.ERROR, colors.WHITE)


def card_style(*, fill: str = colors.WHITE, border: str = colors.HAIRLINE, radius: int = 18) -> dict:
    return {
        "bgcolor": fill,
        "border": ft.Border.all(1, border),
        "border_radius": radius,
        "shadow": ft.BoxShadow(blur_radius=12, spread_radius=0, color=colors.SHADOW, offset=ft.Offset(0, 4)),
    }

