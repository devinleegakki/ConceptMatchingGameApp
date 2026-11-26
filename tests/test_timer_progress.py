from types import SimpleNamespace

import flet as ft

from app import App
from models.card import LevelData
from services.game_engine import GameEngine
from theme import colors


def _level(duration: int = 100) -> LevelData:
    return LevelData(level=1, cards=(), duration_seconds=duration)


def test_timer_progress_color_uses_remaining_time_thresholds():
    assert App.timer_progress_color(1.0) == colors.GREEN_ACCENT
    assert App.timer_progress_color(0.5001) == colors.GREEN_ACCENT
    assert App.timer_progress_color(0.5) == colors.GOLD
    assert App.timer_progress_color(0.2) == colors.ERROR
    assert App.timer_progress_color(0.0) == colors.ERROR


def test_timer_progress_starts_full_and_decreases_with_remaining_time():
    app = App.__new__(App)
    app.level_data = _level()
    app.engine = GameEngine(app.level_data)
    app.game_timer_text = None
    app.game_countdown = ft.ProgressBar(value=0, color=colors.ERROR)
    app.page = SimpleNamespace(update=lambda: None)

    app.update_timer_controls(app.engine)
    assert app.game_countdown.value == 1.0
    assert app.game_countdown.color == colors.GREEN_ACCENT

    app.engine.state.remaining_seconds = 50
    app.update_timer_controls(app.engine)
    assert app.game_countdown.value == 0.5
    assert app.game_countdown.color == colors.GOLD

    app.engine.state.remaining_seconds = 20
    app.update_timer_controls(app.engine)
    assert app.game_countdown.value == 0.2
    assert app.game_countdown.color == colors.ERROR
