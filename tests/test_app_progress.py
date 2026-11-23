from types import SimpleNamespace

import flet as ft

from app import App, Score
from models.card import Card, LevelData
from services.game_engine import GameEngine


def test_record_score_upgrades_failed_level_when_retry_succeeds():
    app = App.__new__(App)
    app.scores = []

    app.record_score(SimpleNamespace(level=2, steps=3, remaining_seconds=0, max_combo=0, is_failed=True))
    app.record_score(SimpleNamespace(level=2, steps=2, remaining_seconds=20, max_combo=2, is_failed=False))

    assert app.scores == [Score(2, 2, 20, 2, False)]


def test_record_score_does_not_duplicate_completed_level():
    app = App.__new__(App)
    app.scores = [Score(1, 4, 30, 2, False)]

    app.record_score(SimpleNamespace(level=1, steps=3, remaining_seconds=40, max_combo=3, is_failed=False))

    assert app.scores == [Score(1, 4, 30, 2, False)]


def test_second_level_cards_use_compact_height():
    app = App.__new__(App)
    app.page = SimpleNamespace(controls=[], clean=lambda: app.page.controls.clear(), add=lambda control: app.page.controls.append(control), update=lambda: None)
    app.level_data = LevelData(2, tuple(Card(str(i), str(i // 2), "question", "x") for i in range(12)), 60)
    app.engine = GameEngine(app.level_data)
    app.feedback_status = None
    app.feedback_cards = []
    app.feedback_explanation = None
    app.pair_slots = [None, None]
    app.pair_locked_type = None
    app.pair_zone_hover = False
    app.pair_hover_slot = None
    app.pair_hover_card_id = None
    app.pair_zone_visuals = []
    app.pair_workspace_visual = None
    app.shell = lambda content, dark=False: content

    app.show_game()

    game_column = app.page.controls[0]
    card_grid = game_column.controls[1]
    first_card = card_grid.content.controls[0].controls[0]
    assert isinstance(first_card, ft.Draggable)
    assert first_card.content.height == 96


def test_narrow_game_layout_keeps_cards_and_pair_slots_inside_surfaces():
    app = App.__new__(App)
    app.page = SimpleNamespace(width=320, controls=[], clean=lambda: app.page.controls.clear(), add=lambda control: app.page.controls.append(control), update=lambda: None)
    app.level_data = LevelData(2, tuple(Card(str(i), str(i // 2), "question", "x") for i in range(12)), 60)
    app.engine = GameEngine(app.level_data)
    app.feedback_status = None
    app.feedback_cards = []
    app.feedback_explanation = None
    app.pair_slots = [None, None]
    app.pair_locked_type = None
    app.pair_zone_hover = False
    app.pair_hover_slot = None
    app.pair_hover_card_id = None
    app.pair_zone_visuals = []
    app.pair_workspace_visual = None
    app.shell = lambda content, dark=False: content

    app.show_game()

    game_column = app.page.controls[0]
    grid = game_column.controls[1]
    first_row = grid.content.controls[0]
    assert sum(card.content.width for card in first_row.controls) + 8 * 3 <= app.game_layout_width()
    assert app.pair_zone_visuals[0].width == app.pair_zone_visuals[1].width
    assert app.pair_zone_visuals[0].width * 2 + 10 <= app.game_layout_width()
