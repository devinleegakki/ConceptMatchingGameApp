"""Profile and ranking share the same Sheets client as level settlement."""
import re
import time

import flet as ft

from components.design_system import section_title, surface, text
from services.sheets_scores import ScoreServiceError


class ScorePages:
    cache_ttl = 30.0

    def __init__(self, app):
        self.app = app
        self.client = app.cloud
        self.panel = None
        self.changing_account = False
        self._cache = {}

    def leave(self):
        self.panel = None

    def invalidate_cache(self, kind=None):
        if kind is None:
            self._cache.clear()
        else:
            self._cache.pop(kind, None)

    def open(self, kind, *, force=False):
        title = "Player profile" if kind == "profile" else "Leaderboard"
        panel = ft.Column([section_title(title), ft.ProgressBar()], expand=True, scroll=ft.ScrollMode.AUTO)
        self.panel = panel
        page = self.app.page
        page.clean()
        page.add(self.app.shell(panel, show_bottom_nav=True, selected_nav=2 if kind == "profile" else 1))
        page.update()
        cached = None if force else self._cache.get(kind)
        if cached is not None:
            data, stored_at = cached
            self.render(panel, kind, data)
            if time.monotonic() - stored_at < self.cache_ttl:
                return
        page.run_task(self.load, panel, kind)

    async def load(self, panel, kind):
        try:
            data = await self.client.view(kind)
        except (ScoreServiceError, RuntimeError, ValueError) as error:
            self.error(panel, kind, str(error))
            return
        if self.panel is not panel:
            return
        self._cache[kind] = (data, time.monotonic())
        self.render(panel, kind, data)

    def render(self, panel, kind, data):
        if self.panel is not panel:
            return
        if kind == "profile":
            controls = self.profile(panel, data)
        else:
            controls = [section_title("Leaderboard", "Each player’s best completed two-level run.")]
            last_score = None
            ranked = sorted(
                data,
                key=lambda row: (-int(row["points"]), str(row["name"]).casefold()),
            )
            for index, row in enumerate(ranked, 1):
                points = int(row["points"])
                if points != last_score:
                    rank = index
                last_score = points
                name = str(row["name"]) + (" (you)" if row["me"] else "")
                controls.append(surface(ft.Text(f'#{rank}   {name}     {points} / 200')))
            if not data:
                controls.append(text("Complete both levels in one run to post the first score.", 15))
        controls.append(self.app.pill("Refresh", lambda _: self.open(kind, force=True), primary=False))
        panel.controls = controls
        panel.update()

    def error(self, panel, kind, message):
        if self.panel is not panel:
            return
        count = len(self.client.pending)
        controls = [section_title("Player profile" if kind == "profile" else "Leaderboard"), ft.Text(message)]
        if kind == "profile" and self.client.identity:
            controls.insert(1, ft.Text(self.client.identity["name"]))
        if count:
            controls.append(ft.Text(f"{count} result(s) on this device waiting to sync."))
        controls.append(self.app.pill("Retry", lambda _: self.open(kind, force=True)))
        panel.controls = controls
        panel.update()

    def profile(self, panel, data):
        best = data["best"]
        controls = [
            section_title(data["name"], "Guest player" if data["kind"] == "guest" else "Player account"),
            surface(ft.Column([ft.Text(f'Attempts: {data["attempts"]}    Levels passed: {data["passed"]}'),
                               ft.Text(f"Best full run: {best} / 200" if best is not None else "Best full run: —")])),
            section_title("Recent attempts"),
        ]
        for row in data["history"][:5]:
            status = "Time out" if row["failed"] else "Passed"
            controls.append(ft.Text(f'{str(row["date"])[:10]}   Level {row["level"]} · {status} · {row["points"]}/100'))
        if not data["history"]:
            controls.append(ft.Text("Your next result will appear here."))
        message = ft.Text()
        async def submit(operation):
            if self.panel is not panel or panel.disabled:
                return
            panel.disabled = True
            self.changing_account = True
            panel.update()
            try:
                await operation()
            except (ScoreServiceError, RuntimeError, ValueError) as error:
                message.value = str(error)
            else:
                if self.panel is panel:
                    self.app.scores.clear()
                    self.app.level_points.clear()
                    self.invalidate_cache()
                    self.open("profile", force=True)
            finally:
                self.changing_account = False
                if self.panel is panel:
                    panel.disabled = False
                    panel.update()

        if data["kind"] == "guest":
            name = ft.TextField(label="Player nickname", max_length=28)
            code = ft.TextField(label="Existing account sign-in code", password=True)
            async def register(_):
                await submit(lambda: self.client.register((name.value or "").strip()))
            async def login(_):
                value = (code.value or "").strip().lower()
                if not re.fullmatch("[0-9a-f]{32}", value):
                    message.value = "Enter the 32-character private code from your player profile."
                    panel.update()
                    return
                await submit(lambda: self.client.sign_in(value))
            controls.extend([name, self.app.pill("Create account with my guest history", register),
                             code, self.app.pill("Sign in", login, primary=False)])
        else:
            key = ft.TextField(label="Private sign-in code · save to sign in on another device",
                               value=self.client.identity["key"], password=True, can_reveal_password=True,
                               read_only=True)
            async def logout(_):
                await submit(self.client.sign_out)
            controls.extend([key, self.app.pill("Sign out and play as guest", logout, primary=False)])
        controls.append(message)
        return controls
