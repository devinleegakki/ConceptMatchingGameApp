"""Scoring version 1: round the combined points once, half up."""
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class Points:
    match: Fraction
    combo: Fraction
    time: Fraction

    @property
    def total(self):
        return int(self.match + self.combo + self.time + Fraction(1, 2))


def calculate_points(matched, pairs, steps, best_combo, remaining, duration, failed):
    match = max(Fraction(0), Fraction(70 * matched, pairs) - 5 * (steps - matched))
    combo = Fraction(20 * best_combo, pairs)
    time = Fraction(0) if failed else Fraction(10 * remaining, duration)
    return Points(match, combo, time)
