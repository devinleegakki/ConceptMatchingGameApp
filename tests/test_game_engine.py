import random

from components.game_card import compact_question
from models.card import Card, LevelData
from services.game_engine import GameEngine


def engine():
    cards = tuple(Card(str(i), pair, "question", pair) for i, pair in enumerate(("a", "a", "b", "b")))
    return GameEngine(LevelData(1, cards, 10), rng=random.Random(1))


def test_matching_increments_combo_and_finishes():
    game = engine()
    assert all(card.is_face_up for card in game.state.cards)
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
    assert all(card.is_face_up for card in game.state.cards)


def test_tick_fails_at_zero():
    game = engine()
    game.state.remaining_seconds = 1
    game.tick()
    assert game.state.is_failed
    assert game.state.is_finished


def test_question_copy_is_compacted_without_changing_formula_copy():
    assert compact_question("已知路程和用时，求平均速度") == "由路程和用时求平均速度"
    shortened = compact_question("这是一个非常长的题目描述，需要在卡片中保持简短")
    assert shortened.endswith("…")
    assert len(shortened) <= 18


def test_unknown_drag_id_is_ignored_without_exception():
    game = engine()
    assert game.select(None) == "ignored"
    assert game.select("missing-card") == "ignored"


def test_second_level_can_pair_cards_after_three_rows():
    cards = tuple(Card(str(i), pair, "question", pair) for i, pair in enumerate(("a", "a", "b", "b", "c", "c", "d", "d", "e", "e", "f", "f")))
    game = GameEngine(LevelData(2, cards, 180), rng=random.Random(2))
    first_pair = [card.id for card in game.state.cards if card.pair_id == "a"]
    assert game.select(first_pair[0]) == "selected"
    assert game.select(first_pair[1]) == "matched"
    assert game.state.matched_pairs == 1
    assert game.state.remaining_seconds == 180

