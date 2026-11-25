"""Guard against Chinese strings leaking back into the rendered UI.

Renders every screen the app can show and walks the resulting control tree,
asserting that no visible text contains CJK characters. This catches strings
that a plain source grep would miss, such as values composed at runtime.
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import flet as ft

from app import App
from components.score_pages import ScorePages
from services.scoring import calculate_points
from models.card import Card, LevelData
from services.game_engine import GameEngine


class FakePage:
    width = 440

    def __init__(self):
        self.controls = []

    def clean(self):
        self.controls.clear()

    def add(self, control):
        self.controls.append(control)

    def update(self):
        pass

    def run_task(self, task, *args):
        asyncio.run(task(*args))


def _level() -> LevelData:
    cards = []
    for pair in range(4):
        cards.append(Card(f"q{pair}", f"p{pair}", "question", f"Q{pair}", "why"))
        cards.append(Card(f"f{pair}", f"p{pair}", "formula", f"F{pair}", "why"))
    return LevelData(1, tuple(cards), 120)


def _app() -> App:
    app = App.__new__(App)
    app.page = FakePage()
    app.is_web_preview = False
    app.level_data = _level()
    app.engine = GameEngine(app.level_data)
    app.scores = []
    app.cloud = SimpleNamespace(view=AsyncMock(side_effect=lambda kind: {
        "leaderboard": [{"name": "Guest-Robin", "points": 170, "me": True}],
        "profile": {"name": "Guest-Robin", "kind": "guest", "attempts": 2,
                    "passed": 2, "best": 170, "history": []},
    }[kind]))
    app.score_pages = ScorePages(app)
    app.level_points = {1: calculate_points(4, 4, 5, 3, 60, 120, False)}
    app.pair_slots = [None, None]
    app.pair_zone_visuals = []
    app.pair_workspace_visual = None
    app.pair_locked_type = None
    app.pair_zone_hover = False
    app.pair_hover_slot = None
    app.pair_hover_card_id = None
    app.feedback_status = None
    app.feedback_cards = []
    app.feedback_explanation = None
    app.game_timer_text = None
    app.game_countdown = None
    app.combo_badge = None
    app.home_page_index = 0
    app.home_pager = None
    app.home_page_dots = []
    return app


def _walk(control, out: list[str], seen: set[int]) -> None:
    """Collect every visible string inside a control tree.

    Flet stores declared properties in the private ``_values`` dict and only a
    few collection attributes (``controls``, ``sizes``) on the instance, so both
    sources have to be merged -- walking ``vars()`` alone finds nothing.
    """
    if id(control) in seen:
        return
    seen.add(id(control))
    if isinstance(control, ft.Text) and control.value:
        out.append(str(control.value))
    fields = dict(getattr(control, "_values", None) or {})
    for name, value in vars(control).items():
        if not name.startswith("_"):
            fields[name] = value
    for value in fields.values():
        try:
            if isinstance(value, ft.Control):
                _walk(value, out, seen)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    if isinstance(item, ft.Control):
                        _walk(item, out, seen)
        except Exception:
            # A property may not be readable before the control is mounted.
            continue


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _collect(app: App) -> list[str]:
    texts: list[str] = []
    seen: set[int] = set()
    for control in app.page.controls:
        _walk(control, texts, seen)
    return texts


def test_main_screens_render_without_chinese(monkeypatch):
    # The test page has no live Flet connection for the async Sheets panel refresh.
    monkeypatch.setattr(ft.Column, "update", lambda self: None)
    app = _app()
    screens = {
        "home": app.show_home,
        "leaderboard": app.show_leaderboard,
        "profile": app.show_profile,
        "instructions": app.show_instructions,
        "loading": lambda: app.show_loading(1),
        "board": app.show_game,
        "level result": app.show_level_result,
        "summary": app.show_summary,
    }
    for name, render in screens.items():
        render()
        texts = _collect(app)
        found = [text for text in texts if _has_cjk(text)]
        assert not found, f"{name} screen still shows Chinese: {found}"
        expected = {"profile": "Guest-Robin", "leaderboard": "#1   Guest-Robin (you)     170 / 200",
                    "level result": "85 / 100", "summary": "85 / 200"}
        if name in expected:
            assert expected[name] in texts


def test_error_message_from_csv_loader_is_english():
    from services.csv_loader import DataError, parse_csv

    try:
        parse_csv("", 1)
    except DataError as exc:
        assert not _has_cjk(str(exc))
    else:
        raise AssertionError("empty CSV should raise DataError")


def test_card_labels_are_english():
    app = _app()
    app.show_game()
    texts = _collect(app)
    # Cards carry a single-letter tag so the label fits a 69px card.
    assert any(text in {"Q", "F"} for text in texts)
