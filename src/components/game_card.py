import flet as ft

from models.card import Card
from theme import colors


def game_card(card: Card, on_tap, *, selected: bool = False, width: int = 150, height: int = 110) -> ft.Control:
    if card.is_matched:
        return ft.Container(width=width, height=height, opacity=0.0)
    face = card.content
    fill = colors.AMBER if selected else colors.SURFACE
    label = "题目" if card.type == "question" else "公式"
    body = ft.Column(
        [
            ft.Text(label.upper(), size=10, weight=ft.FontWeight.BOLD, color=colors.CHROME_INDIGO),
            ft.Text(face, size=16, weight=ft.FontWeight.BOLD, color=colors.INK, text_align=ft.TextAlign.CENTER),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=6,
    )
    control = ft.Container(
        content=body,
        width=width,
        height=height,
        padding=10,
        bgcolor=fill,
        border=ft.Border.all(3 if selected else 2, colors.SIGNAL if selected else colors.CHROME_INDIGO),
        border_radius=6,
        on_click=lambda _: on_tap(card.id),
        animate=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
    )
    return ft.Draggable(content=control, data=card.id, group="cards")

