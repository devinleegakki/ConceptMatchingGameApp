import flet as ft

from app import App
from components.design_system import combo_badge
from models.card import Card, LevelData
from services.game_engine import GameEngine
from theme import colors


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


def _level() -> LevelData:
    cards = []
    for pair in range(4):
        cards.append(Card(f"q{pair}", f"p{pair}", "question", f"Q{pair}", "why"))
        cards.append(Card(f"f{pair}", f"p{pair}", "formula", f"F{pair}", "why"))
    return LevelData(1, tuple(cards), 120)


def _app_with_combo(combo: int) -> App:
    app = App.__new__(App)
    app.page = FakePage()
    app.is_web_preview = False
    app.level_data = _level()
    app.engine = GameEngine(app.level_data)
    app.engine.state.combo = combo
    app.engine.state.steps = 3
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
    return app


def test_broken_chain_stays_neutral_mint():
    assert combo_badge(0).bgcolor == colors.GREEN_LIGHT


def test_short_chain_turns_gold():
    assert combo_badge(1).bgcolor == colors.GOLD
    assert combo_badge(2).bgcolor == colors.GOLD


def test_chain_of_three_or_more_turns_hot():
    assert combo_badge(3).bgcolor == colors.ERROR
    assert combo_badge(9).bgcolor == colors.ERROR


def test_chip_reports_the_chain_count():
    assert combo_badge(4).content.value == "Chain ×4"


def test_chip_declares_the_scale_pop():
    chip = combo_badge(2)
    assert chip.animate_scale is not None
    assert chip.scale is not None
    assert chip.scale.scale == 1.0


def test_game_board_keeps_a_reference_to_the_live_chip():
    app = _app_with_combo(3)
    app.show_game()
    assert app.combo_badge is not None
    assert app.combo_badge.bgcolor == colors.ERROR
    assert isinstance(app.page.controls[0], ft.Control)
