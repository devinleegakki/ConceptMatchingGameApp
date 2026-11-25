from pathlib import Path

import pytest

from services.csv_loader import DataError, parse_csv


CSV = Path(__file__).parents[1].joinpath("data", "sample_cards.csv").read_text(encoding="utf-8")


def test_loads_both_levels():
    assert len(parse_csv(CSV, 1).cards) == 8
    assert len(parse_csv(CSV, 2).cards) == 12
    assert parse_csv(CSV, 1).duration_seconds == 120


def test_rejects_invalid_pair_count():
    # Match on the stable prefix (level,order,pair_id) only, so rewording the
    # card text never breaks this test.
    broken = CSV.replace("1,8,work,", "1,8,other,")
    with pytest.raises(DataError, match="pair_id"):
        parse_csv(broken, 1)


def test_rejects_missing_columns():
    with pytest.raises(DataError, match="missing required columns"):
        parse_csv("level,order,pair_id\n1,1,a,\n", 1)

