import random

from models.card import Card, LevelData
from services.game_engine import GameEngine


def engine():
    cards = tuple(Card(str(i), pair, "question", pair) for i, pair in enumerate(("a", "a", "b", "b")))
    return GameEngine(LevelData(1, cards, 10), rng=random.Random(1))


def test_matching_increments_combo_and_finishes():
    game = engine()
    ids = {card.pair_id: [card.id for card in game.state.cards if card.pair_id == card.pair_id] for card in game.state.cards}
    a = [card.id for card in game.state.cards if card.pair_id == "a"]
    assert game.select(a[0]) == "selected"
    assert game.select(a[1]) == "matched"
    assert game.state.combo == 1
    assert game.state.steps == 1


def test_mismatch_locks_then_resolves():
    game = engine()
    a = next(card.id for card in game.state.cards if card.pair_id == "a")
    b = next(card.id for card in game.state.cards if card.pair_id == "b")
    game.select(a)
    assert game.select(b) == "mismatch"
    assert game.state.is_locked
    assert game.select(a) == "ignored"
    game.resolve_mismatch()
    assert not game.state.is_locked
    assert game.state.combo == 0


def test_tick_fails_at_zero():
    game = engine()
    game.state.remaining_seconds = 1
    game.tick()
    assert game.state.is_failed
    assert game.state.is_finished

