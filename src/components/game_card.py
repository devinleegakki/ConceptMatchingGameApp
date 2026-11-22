import flet as ft

from models.card import Card
from theme import colors
from theme import typography


def game_card(card: Card, on_tap, *, selected: bool = False, width: int = 150, height: int = 124) -> ft.Control:
    if card.is_matched:
        return ft.Container(width=width, height=height, opacity=0.0)
    face = card.content
    fill = colors.GREEN_LIGHT if selected else colors.WHITE
    label = "题目" if card.type == "question" else "公式"
    text_size = 13 if len(face) > 20 else 16
    body = ft.Column(
        [
            ft.Text(label, size=11, weight=ft.FontWeight.W_600, color=colors.STARBUCKS_GREEN, font_family=typography.FONT_FAMILY),
            ft.Text(face, size=text_size, weight=ft.FontWeight.W_600, color=colors.INK, text_align=ft.TextAlign.CENTER, font_family=typography.FONT_FAMILY, max_lines=5, overflow=ft.TextOverflow.VISIBLE),
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
        border=ft.Border.all(2 if selected else 1, colors.GREEN_ACCENT if selected else colors.HAIRLINE),
        border_radius=12,
        shadow=ft.BoxShadow(blur_radius=4, spread_radius=0, color="#24000000", offset=ft.Offset(0, 1)),
        on_click=lambda _: on_tap(card.id),
        animate=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
    )
    return ft.Draggable(content=control, data=card.id, group="cards")

