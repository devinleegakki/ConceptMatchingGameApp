import random

from models.card import Card, LevelData
from models.game_state import GameState


class GameEngine:
    def __init__(self, level_data: LevelData, *, rng: random.Random | None = None):
        cards = list(level_data.cards)
        (rng or random).shuffle(cards)
        self.state = GameState(level_data.level, cards, [], 0, level_data.duration_seconds)

    def card(self, card_id: str) -> Card | None:
        return next((card for card in self.state.cards if card.id == str(card_id)), None)

    def select(self, card_id: str) -> str:
        state = self.state
        if state.is_locked or state.is_finished or state.is_failed:
            return "ignored"
        card = self.card(card_id)
        if card is None:
            return "ignored"
        card_id = str(card_id)
        if card.is_matched or card_id in state.selected_card_ids:
            return "ignored"
        state.selected_card_ids.append(card_id)
        if len(state.selected_card_ids) < 2:
            return "selected"
        state.steps += 1
        first, second = (self.card(item_id) for item_id in state.selected_card_ids)
        if first is None or second is None:
            state.selected_card_ids.clear()
            return "ignored"
        if first.pair_id == second.pair_id:
            state.cards = [item.matched() if item.id in state.selected_card_ids else item for item in state.cards]
            state.matched_pairs += 1
            state.combo += 1
            state.max_combo = max(state.max_combo, state.combo)
            state.selected_card_ids.clear()
            if state.matched_pairs == len(state.cards) // 2:
                state.is_finished = True
            return "matched"
        state.is_locked = True
        state.combo = 0
        return "mismatch"

    def resolve_mismatch(self) -> None:
        self.state.selected_card_ids.clear()
        self.state.is_locked = False

    def tick(self) -> bool:
        if self.state.is_finished or self.state.is_failed:
            return False
        self.state.remaining_seconds = max(0, self.state.remaining_seconds - 1)
        if self.state.remaining_seconds == 0:
            self.state.is_failed = True
            self.state.is_finished = True
        return True

