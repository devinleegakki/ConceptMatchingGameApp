"""Generate the Concept Match app icon (1024x1024 PNG).

Visual: deep house-green field, one question card and one formula card,
joined by a gold seal carrying an equals sign -- the pairing idea in one mark.
Colors are lifted from src/theme/colors.py so the icon matches the UI.
"""
from pathlib import Path

from PIL import Image, ImageDraw

SS = 4  # supersampling factor for clean edges
OUT = 1024

BG = (30, 57, 50)        # HOUSE_GREEN  #1E3932
GOLD = (224, 168, 58)    # GOLD         #e0a83a
CARD_Q = (247, 240, 231)  # QUESTION_SURFACE #f7f0e7
CARD_F = (231, 243, 238)  # FORMULA_SURFACE  #e7f3ee
ACC_Q = (224, 168, 58)   # question accent  GOLD
ACC_F = (0, 117, 74)     # formula accent   GREEN_ACCENT
RULE_Q = (214, 199, 178)  # muted rule on the cream card
RULE_F = (176, 208, 195)  # muted rule on the mint card
WHITE = (255, 255, 255)


def main() -> None:
    size = OUT * SS
    img = Image.new("RGB", (size, size), BG)
    d = ImageDraw.Draw(img)

    def box(bbox):
        return [int(v * SS) for v in bbox]

    def card(bbox, fill, accent, rule, rules):
        d.rounded_rectangle(box(bbox), radius=int(34 * SS), fill=fill)
        x0, y0 = bbox[0], bbox[1]
        # Vertically centre the marker + rules block inside the card so the
        # top and bottom margins stay even.
        marker_top = y0 + 77
        d.rounded_rectangle(
            box((x0 + 44, marker_top, x0 + 84, marker_top + 40)),
            radius=int(10 * SS),
            fill=accent,
        )
        # abstract text rules, decreasing width; keep clear of the right padding
        for index, width in enumerate(rules):
            top = y0 + 149 + index * 74
            d.rounded_rectangle(
                box((x0 + 44, top, x0 + 44 + width, top + 26)),
                radius=int(13 * SS),
                fill=rule,
            )

    # two cards, deliberately offset so the mark does not read as symmetric
    card((116, 300, 456, 700), CARD_Q, ACC_Q, RULE_Q, (220, 176, 128))
    card((568, 324, 908, 724), CARD_F, ACC_F, RULE_F, (220, 172, 120))

    # gold seal in the gap between the cards
    cx, cy, r = 512, 512, 74
    d.ellipse(box((cx - r, cy - r, cx + r, cy + r)), fill=GOLD)
    bar_h, bar_w = 17, 72
    for offset in (-19, 19):
        top = cy + offset - bar_h // 2
        d.rounded_rectangle(
            box((cx - bar_w // 2, top, cx + bar_w // 2, top + bar_h)),
            radius=int(bar_h * SS / 2),
            fill=BG,
        )

    out = img.resize((OUT, OUT), Image.LANCZOS)
    target = Path(__file__).resolve().parent.parent / "assets" / "icon.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    out.save(target, "PNG", optimize=True)
    print(f"wrote {target}  {out.size[0]}x{out.size[1]}")


if __name__ == "__main__":
    main()
