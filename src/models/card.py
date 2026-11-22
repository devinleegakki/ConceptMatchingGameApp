from dataclasses import dataclass


@dataclass(frozen=True)
class Card:
    id: str
    pair_id: str
    type: str
    content: str
    explanation: str | None = None
    # Cards are readable from the start; this game tests concept association,
    # rather than memory of hidden cards.
    is_face_up: bool = True
    is_matched: bool = False

    def face_up(self) -> "Card":
        return Card(self.id, self.pair_id, self.type, self.content, self.explanation, True, self.is_matched)

    def matched(self) -> "Card":
        return Card(self.id, self.pair_id, self.type, self.content, self.explanation, True, True)

    def face_down(self) -> "Card":
        return self


@dataclass(frozen=True)
class LevelData:
    level: int
    cards: tuple[Card, ...]
    duration_seconds: int

