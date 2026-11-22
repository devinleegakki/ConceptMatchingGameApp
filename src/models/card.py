from dataclasses import dataclass


@dataclass(frozen=True)
class Card:
    id: str
    pair_id: str
    type: str
    content: str
    explanation: str | None = None
    is_face_up: bool = False
    is_matched: bool = False

    def face_up(self) -> "Card":
        return Card(self.id, self.pair_id, self.type, self.content, self.explanation, True, self.is_matched)

    def matched(self) -> "Card":
        return Card(self.id, self.pair_id, self.type, self.content, self.explanation, True, True)

    def face_down(self) -> "Card":
        return Card(self.id, self.pair_id, self.type, self.content, self.explanation, False, self.is_matched)


@dataclass(frozen=True)
class LevelData:
    level: int
    cards: tuple[Card, ...]
    duration_seconds: int

