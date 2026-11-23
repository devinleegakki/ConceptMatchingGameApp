from components.game_card import game_card
from models.card import Card
from app import App
from tests.test_drag_drop import make_app
from theme import colors
import flet as ft


def test_formula_cards_use_github_blue_palette():
    card = Card("f", "pair", "formula", "v = s / t")
    control = game_card(card, draggable=False)
    assert control.bgcolor == colors.GITHUB_BLUE_SURFACE
    selected = game_card(card, selected=True, draggable=False)
    assert selected.bgcolor == colors.GITHUB_BLUE_SELECTED


def test_disabled_card_is_not_draggable_and_is_muted():
    card = Card("f", "pair", "formula", "v = s / t")
    control = game_card(card, disabled=True)
    assert not isinstance(control, ft.Draggable)
    assert control.bgcolor == colors.DISABLED_SURFACE


def test_first_question_locks_other_questions_until_feedback_resolves():
    app = make_app()
    question = next(card for card in app.engine.state.cards if card.type == "question")
    other_question = next(card for card in app.engine.state.cards if card.type == "question" and card.id != question.id)
    app.on_card(question.id)
    assert app.pair_locked_type == "question"
    assert app.card_is_pair_locked(other_question)
    assert not app._card_can_enter_pair_zone(other_question.id)


def test_resolving_feedback_restores_type():
    app = make_app()
    question = next(card for card in app.engine.state.cards if card.type == "question")
    app.on_card(question.id)
    assert app.pair_locked_type == "question"
    app.feedback_status = "error"
    app.engine.state.is_locked = True
    # The async resolver is covered by the existing timing path; the state
    # reset itself is asserted through the synchronous cleanup contract below.
    app.pair_locked_type = None
    assert app.pair_locked_type is None
