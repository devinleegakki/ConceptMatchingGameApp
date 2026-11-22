import flet as ft
import re

from models.card import Card
from theme import colors
from theme import typography


QUESTION_SHORTCUTS = {
    "已知路程和用时，求平均速度": "由路程和用时求平均速度",
    "质量和加速度已知，求力": "由质量和加速度求力",
    "质量与体积已知，求密度": "由质量和体积求密度",
    "力与位移同向时求功": "由同向力和位移求功",
    "单位时间内做功的快慢": "判断做功的快慢",
    "单位面积受到的压力": "判断单位面积受力",
    "物体由于运动而具有的能量": "判断物体的运动能量",
    "电流通过导体时两端的电势差": "判断导体两端电压",
    "电路消耗电能的快慢": "判断电路消耗电能快慢",
    "物体吸收或放出的热量": "判断物体吸收或放热量",
}


def compact_question(text: str, limit: int = 18) -> str:
    """Shorten question copy for narrow cards without changing the source CSV."""
    if text in QUESTION_SHORTCUTS:
        return QUESTION_SHORTCUTS[text]
    compacted = re.sub(r"^(已知|已给出)", "由", text)
    compacted = compacted.replace("，求", "求").replace("时求", "求")
    if len(compacted) <= limit:
        return compacted
    return compacted[: limit - 1] + "…"


def game_card(card: Card, on_tap=None, *, selected: bool = False, draggable: bool = True, width: int = 150, height: int = 124) -> ft.Control:
    if card.is_matched:
        return ft.Container(width=width, height=height, opacity=0.0)
    face = compact_question(card.content) if card.type == "question" else card.content
    if card.type == "question":
        fill = colors.QUESTION_SELECTED if selected else colors.QUESTION_SURFACE
    else:
        fill = colors.FORMULA_SELECTED if selected else colors.FORMULA_SURFACE
    label = "题目" if card.type == "question" else "公式"
    text_size = 13 if len(face) > 20 else 16
    body = ft.Column(
        [
            ft.Text(label, size=11, weight=ft.FontWeight.W_600, color=colors.STARBUCKS_GREEN if card.type == "question" else colors.GREEN_ACCENT, font_family=typography.FONT_FAMILY),
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
        animate=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
    )
    if not draggable:
        return control
    return ft.Draggable(content=control, data=card.id, group="cards")

