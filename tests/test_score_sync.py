import asyncio
from types import SimpleNamespace

import pytest

from app import App
from services.scoring import calculate_points
from services.sheets_scores import ScoreServiceError, SheetsScores


class Preferences(dict):
    async def get(self, key):
        return super().get(key)

    async def set(self, key, value):
        self[key] = value
        return True


@pytest.mark.parametrize("inputs,expected", [
    ((4, 4, 5, 3, 60, 120, False), 85),
    ((6, 6, 6, 6, 180, 180, False), 100),
    ((0, 4, 5, 0, 0, 120, True), 0),
    ((2, 4, 3, 2, 0, 120, True), 40),
    ((1, 4, 1, 1, 0, 120, True), 23),
])
def test_score_rules(inputs, expected):
    assert calculate_points(*inputs).total == expected


def test_offline_finish_reopens_and_retries_same_attempt():
    async def scenario():
        preferences = Preferences()
        cloud = SheetsScores(preferences)
        async def offline(*args, **kwargs):
            raise ScoreServiceError("offline")
        cloud._post = offline
        app = App.__new__(App)
        state = SimpleNamespace(level=1, cards=list(range(8)), matched_pairs=4, steps=5,
                                max_combo=3, remaining_seconds=60, is_failed=False)
        app.engine = SimpleNamespace(state=state)
        app.level_data = SimpleNamespace(duration_seconds=120)
        app.run_id, app.attempt_id, app.settled_attempt = "run", "attempt", None
        app.scores, app.level_points, app.cloud = [], {}, cloud
        app.page = SimpleNamespace(run_task=lambda fn: None)
        app.show_level_result = lambda: None
        await app.finish_level()
        await app.finish_level()
        assert len(cloud.pending) == 1
        assert app.level_points[1].total == 85
        with pytest.raises(ScoreServiceError):
            await cloud.sync()
        assert len(cloud.pending) == 1
        again = SheetsScores(preferences)
        sent = []
        async def restored(action, **payload):
            sent.append((action,payload))
            return {"points": 85}
        again._post = restored
        await again.sync()
        assert sent[0][1]["key"] == cloud.identity["key"]
        assert sent[0][1]["attempt"]["attempt_id"] == "attempt"
        await again.sync()
        assert len(sent) == 1
        assert not again.pending
    asyncio.run(scenario())


def test_guest_and_member_profile_controls_build():
    from components.score_pages import ScorePages
    from flet import Column
    app = SimpleNamespace(cloud=SimpleNamespace(identity={"key":"a"*32}), pill=lambda *a, **kw: Column())
    page = ScorePages(app)
    for kind in ("member","guest"):
        controls = page.profile(Column(), {"name":"Guest-Finch","kind":kind,"attempts":1,
            "passed":1,"best":None,"history":[{"date":"2026-11-24","level":1,"points":85,"failed":False}]})
        assert controls


def test_leaderboard_sorts_sheet_rows_and_shares_tied_rank():
    from components.score_pages import ScorePages
    from flet import Column

    class Cloud:
        async def view(self, kind):
            return [{"name": n, "points": s, "me": n == "Ada"}
                    for n, s in [("Bo", 150), ("Zoe", 180), ("Ada", 180)]]

    page = ScorePages(SimpleNamespace(cloud=Cloud(), pill=lambda *a, **kw: Column()))
    page.panel = SimpleNamespace(controls=[], update=lambda: None)
    asyncio.run(page.load(page.panel, "leaderboard"))
    rows = [row.content.value for row in page.panel.controls[1:-1]]
    assert rows == ["#1   Ada (you)     180 / 200", "#1   Zoe     180 / 200", "#3   Bo     150 / 200"]
