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
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        raise DataError(f"CSV 缺少字段：{', '.join(sorted(missing))}")
    rows = [row for row in reader if str(row.get("level", "")).strip() == str(level)]
    expected = 8 if level == 1 else 12 if level == 2 else 0
    if len(rows) != expected:
        raise DataError(f"第 {level} 关需要 {expected} 张卡片，实际为 {len(rows)} 张")
    try:
        rows.sort(key=lambda row: int(row["order"]))
        durations = {int(row["duration_seconds"]) for row in rows}
    except (TypeError, ValueError) as exc:
        raise DataError("order 和 duration_seconds 必须是整数") from exc
    if len(durations) != 1 or next(iter(durations)) <= 0:
        raise DataError("同一关的 duration_seconds 必须是同一个正整数")
    pair_counts = Counter(row["pair_id"].strip() for row in rows)
    if not pair_counts or any(count != 2 for count in pair_counts.values()):
        raise DataError("每个 pair_id 必须正好出现两次")
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
        raise DataError("尚未配置 CSV_URL")
    try:
        response = httpx.get(url, timeout=timeout, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise DataError(f"在线题库加载失败：{exc}") from exc
    return parse_csv(response.text, level)

