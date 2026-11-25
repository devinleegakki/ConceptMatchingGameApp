import flet as ft

from models.card import Card
from theme import colors
from theme import typography


def _fit_text_size(face: str, available: int) -> int:
    """Pick the largest font size whose longest word still fits one line.

    English card faces break mid-word when a single word is wider than the
    card, which looks broken ("Potenti / al"). Shrinking until the longest
    word fits keeps every line break on a word boundary.
    """
    longest = max((len(word) for word in face.split()), default=1)
    for size in (16, 15, 14, 13, 12, 11, 10, 9):
        if longest * size * 0.56 <= available:
            return size
    return 9


def game_card(card: Card, on_tap=None, *, selected: bool = False, draggable: bool = True, disabled: bool = False, width: int = 150, height: int = 124) -> ft.Control:
    if card.is_matched:
        return ft.Container(width=width, height=height, opacity=0.0)
    face = card.content
    if card.type == "question":
        fill = colors.QUESTION_SELECTED if selected else colors.QUESTION_SURFACE
        accent = colors.GOLD
    else:
        fill = colors.GITHUB_BLUE_SELECTED if selected else colors.GITHUB_BLUE_SURFACE
        accent = colors.GITHUB_BLUE
    if disabled:
        fill = colors.DISABLED_SURFACE
        accent = colors.DISABLED_INK
    # Single-letter tag: a full word overflows the 69px-wide card on a 360px
    # screen, and the card face already shows what it is (formula vs question).
    label = "Q" if card.type == "question" else "F"
    padding = 10 if width >= 78 else 8
    text_size = _fit_text_size(face, width - 2 * padding)
    body = ft.Column(
        [
            ft.Row([ft.Text(label, size=11, weight=ft.FontWeight.W_700, color=accent, font_family=typography.FONT_FAMILY), ft.Container(width=6, height=6, bgcolor=accent, border_radius=6)], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
            ft.Text(face, size=text_size, weight=ft.FontWeight.W_600, color=colors.DISABLED_INK if disabled else colors.INK, text_align=ft.TextAlign.CENTER, font_family=typography.FONT_FAMILY, max_lines=6, overflow=ft.TextOverflow.ELLIPSIS),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=6,
    )
    control = ft.Container(
        content=body,
        width=width,
        height=height,
        padding=padding,
        bgcolor=fill,
        border=ft.Border.all(3 if selected else 1, accent if selected else colors.HAIRLINE),
        border_radius=12,
        shadow=ft.BoxShadow(blur_radius=10 if selected else 5, spread_radius=0, color="#30000000", offset=ft.Offset(0, 3)),
        animate=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
    )
    if disabled or not draggable:
        return control
    return ft.Draggable(content=control, data=card.id, group="cards")

