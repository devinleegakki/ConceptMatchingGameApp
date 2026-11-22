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

