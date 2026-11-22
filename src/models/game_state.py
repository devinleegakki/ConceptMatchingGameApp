from dataclasses import dataclass
from .card import Card


@dataclass
class GameState:
    level: int
    cards: list[Card]
    selected_card_ids: list[str]
    steps: int
    remaining_seconds: int
    combo: int = 0
    max_combo: int = 0
    matched_pairs: int = 0
    is_locked: bool = False
    is_finished: bool = False
    is_failed: bool = False

