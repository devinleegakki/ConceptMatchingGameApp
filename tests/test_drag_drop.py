from types import SimpleNamespace

from app import App
from models.card import Card, LevelData
from services.game_engine import GameEngine


def make_app() -> App:
    app = App.__new__(App)
    cards = tuple(
        Card(str(index), pair_id, "question", pair_id)
        for index, pair_id in enumerate(("a", "a", "b", "b"))
    )
    app.engine = GameEngine(LevelData(1, cards, 60))
    app.feedback_status = None
    app.pair_slots = [None, None]
    app.pair_locked_type = None
    app.pair_zone_hover = False
    app.pair_hover_slot = None
    app.pair_hover_card_id = None
    app.pair_zone_visuals = []
    app.pair_workspace_visual = None
    app.refresh_game = lambda: None
    return app


def test_drag_card_id_reads_event_and_source_payloads():
    assert App.drag_card_id(SimpleNamespace(data="event-card")) == "event-card"
    assert App.drag_card_id(SimpleNamespace(src=SimpleNamespace(data="source-card"))) == "source-card"

    source = SimpleNamespace(data="page-card")
    page = SimpleNamespace(get_control=lambda _source_id: source)
    assert App.drag_card_id(SimpleNamespace(src_id=7, page=page)) == "page-card"


def test_pair_zone_accepts_group_hover_without_resolved_payload():
    app = make_app()
    assert app.pair_zone_accepts(SimpleNamespace(accept=True)) is True
    assert app.pair_zone_accepts(SimpleNamespace(accept=False)) is False


def test_first_drop_uses_first_empty_slot_and_duplicate_is_rejected():
    app = make_app()
    card_id = app.engine.state.cards[0].id
    app.pair_zone_accept(SimpleNamespace(data=card_id))
    assert app.pair_slots[0].id == card_id
    assert app.pair_slots[1] is None
    assert app.pair_zone_accepts(SimpleNamespace(data=card_id)) is False


def test_pair_zone_rejects_when_both_slots_are_occupied():
    app = make_app()
    cards = app.engine.state.cards
    app.pair_slots = [cards[0], cards[1]]
    assert app.pair_zone_accepts(SimpleNamespace(data=cards[2].id)) is False
