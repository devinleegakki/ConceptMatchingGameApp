import asyncio
from types import SimpleNamespace

import httpx
import pytest

from app import App
from services.scoring import calculate_points
from services.sheets_scores import ScoreServiceError, SheetsScores, scores_endpoint


class Preferences(dict):
    async def get(self, key):
        return super().get(key)

    async def set(self, key, value):
        self[key] = value
        return True


def test_scores_config_prefers_local_file_and_reloads_edits(tmp_path, monkeypatch):
    cloud = SheetsScores(Preferences())
    cloud.config = tmp_path / "scores_endpoint.txt"
    base = "https://script.google.com/macros/s/"
    env_url = base + "env/exec"
    file_url = base + "file/exec"
    monkeypatch.setenv("SCORES_API_URL", " " + env_url + " ")
    assert scores_endpoint(cloud.config) == env_url
    cloud.config.write_text(file_url + "\n", encoding="utf-8-sig")
    assert scores_endpoint(cloud.config) == file_url
    cloud.config.write_text(file_url.replace("/exec", "/dev"), encoding="utf-8")
    with pytest.raises(ScoreServiceError, match="scores_endpoint.txt"):
        asyncio.run(cloud._post("login"))


@pytest.mark.parametrize("failure, message", [
    ("timeout", "timed out"),
    ("connection", "ConnectError"),
    ("denied", "Access denied"),
    ("login-page", "Access denied"),
    ("missing", "HTTP 404"),
    ("html", "instead of score data"),
])
def test_sync_failure_reports_cause_and_preserves_score(tmp_path, monkeypatch, failure, message):
    cloud = SheetsScores(Preferences())
    cloud.config = tmp_path / "scores_endpoint.txt"
    cloud.config.write_text("https://script.google.com/macros/s/test/exec", encoding="utf-8")

    def respond(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("timeout", request=request)
        if failure == "connection":
            raise httpx.ConnectError("offline", request=request)
        if failure == "login-page" and request.url.host != "accounts.google.com":
            return httpx.Response(302, headers={"Location": "https://accounts.google.com/login"})
        status = {"denied": 403, "missing": 404}.get(failure, 200)
        return httpx.Response(status, text="<html></html>")

    client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: client(transport=httpx.MockTransport(respond), **kw))

    async def scenario():
        await cloud.enqueue({"attempt_id": "saved"})
        with pytest.raises(ScoreServiceError, match=message):
            await cloud.view("profile")
        restored = SheetsScores(cloud.preferences)
        await restored._load()
        assert restored.pending == [{"attempt_id": "saved"}]

    asyncio.run(scenario())


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
