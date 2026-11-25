import csv
import io
from collections import Counter
from typing import Iterable

import httpx

from models.card import Card, LevelData

REQUIRED_COLUMNS = {"level", "order", "pair_id", "type", "content", "explanation", "duration_seconds"}


class DataError(ValueError):
    pass


def parse_csv(text: str, level: int) -> LevelData:
    if not text.strip():
        raise DataError("The online question bank is empty. Add the schema columns and card rows in Google Sheets first.")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        raise DataError(f"CSV is missing required columns: {', '.join(sorted(missing))}")
    rows = [row for row in reader if str(row.get("level", "")).strip() == str(level)]
    expected = 8 if level == 1 else 12 if level == 2 else 0
    if len(rows) != expected:
        raise DataError(f"Level {level} needs {expected} cards but the sheet returned {len(rows)}.")
    try:
        rows.sort(key=lambda row: int(row["order"]))
        durations = {int(row["duration_seconds"]) for row in rows}
    except (TypeError, ValueError) as exc:
        raise DataError("order and duration_seconds must be integers.") from exc
    if len(durations) != 1 or next(iter(durations)) <= 0:
        raise DataError("Every row in a level must share one positive duration_seconds.")
    pair_counts = Counter(row["pair_id"].strip() for row in rows)
    if not pair_counts or any(count != 2 for count in pair_counts.values()):
        raise DataError("Each pair_id must appear exactly twice.")
    cards = tuple(
        Card(
            id=f"l{level}_c{index + 1}",
            pair_id=row["pair_id"].strip(),
            type=row["type"].strip(),
            content=row["content"].strip(),
            explanation=row.get("explanation", "").strip() or None,
        )
        for index, row in enumerate(rows)
    )
    return LevelData(level=level, cards=cards, duration_seconds=next(iter(durations)))


def load_level(url: str, level: int, timeout: float = 10.0) -> LevelData:
    if not url:
        raise DataError("CSV_URL is not configured.")
    try:
        response = httpx.get(url, timeout=timeout, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise DataError(f"Could not load the online question bank: {exc}") from exc
    return parse_csv(response.text, level)

