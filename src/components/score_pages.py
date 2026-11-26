"""Profile and ranking share the same Sheets client as level settlement."""
import re
import time

import flet as ft

from components.design_system import section_title, surface, text
from services.sheets_scores import ScoreServiceError
from theme import colors


def rank_of(best) -> str:
    """Best full run (out of 200) mapped to the team's four rank names."""
    if best is None:
        return "Unranked"
    if best >= 180:
        return "Concept Master"
    if best >= 150:
        return "Link Master"
    if best >= 100:
        return "Learning Explorer"
    return "Concept Rookie"


def initials_of(name: str) -> str:
    parts = [part for part in str(name).replace("-", " ").split() if part]
    return ("".join(part[0] for part in parts[:2]) or "?").upper()


def podium_step(row: dict, height: int, *, champion: bool) -> ft.Control:
    """One column of the top-three podium, sitting on a House Green band."""
    fill = colors.GOLD if champion else colors.GREEN_UPLIFT
    ink = colors.HOUSE_GREEN if champion else "#d9e8e2"
    label = colors.WHITE if champion else "#b7d7ca"
    name = f"{row['name']}\nYou" if row["me"] else str(row["name"])
    return ft.Container(
        ft.Column(
            [
                ft.Container(
                    text(name, 11, color=label, weight=ft.FontWeight.W_700, max_lines=2, text_align=ft.TextAlign.CENTER),
                    padding=ft.Padding.symmetric(horizontal=4),
                ),
                ft.Container(
                    ft.Column(
                        [
                            ft.Text(str(int(row["points"])), size=19 if champion else 16, color=ink, weight=ft.FontWeight.W_700, font_family="system-ui"),
                            ft.Text("pts", size=9, color=ink, font_family="system-ui"),
                        ],
                        spacing=0,
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    height=height,
                    bgcolor=fill,
                    border_radius=ft.BorderRadius.only(top_left=10, top_right=10),
                    alignment=ft.Alignment(0, 0),
                ),
            ],
            spacing=6,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        expand=True,
    )


def rank_row(position: int, row: dict) -> ft.Control:
    """A rank line below the podium; the local player keeps a mint highlight."""
    mine = bool(row["me"])
    parts: list[ft.Control] = [
        text(f"{position:02d}", 12, color=colors.GREEN_ACCENT if mine else colors.INK_LIGHT, weight=ft.FontWeight.W_700),
        text(str(row["name"]), 14, color=colors.HOUSE_GREEN, weight=ft.FontWeight.W_700 if mine else None, max_lines=1),
    ]
    if mine:
        parts.append(
            ft.Container(
                text("YOU", 9, color=colors.GREEN_ACCENT, weight=ft.FontWeight.W_700),
                border=ft.Border.all(1, colors.GREEN_ACCENT),
                border_radius=20,
                padding=ft.Padding.symmetric(horizontal=6, vertical=1),
            )
        )
    parts.append(ft.Container(expand=True))
    parts.append(
        ft.Container(
            text(f'{int(row["points"])}/200', 12, color=colors.GREEN_ACCENT if mine else colors.INK, weight=ft.FontWeight.W_700),
            bgcolor=colors.WHITE if mine else colors.NEUTRAL_WARM,
            border_radius=20,
            padding=ft.Padding.symmetric(horizontal=10, vertical=5),
        )
    )
    return ft.Container(
        ft.Row(parts, spacing=8),
        bgcolor=colors.GREEN_LIGHT if mine else colors.WHITE,
        border=ft.Border.all(1, colors.HAIRLINE),
        border_radius=16,
        padding=ft.Padding.symmetric(horizontal=14, vertical=12),
    )


def metric(label: str, value: str) -> ft.Container:
    return surface(
        ft.Column([text(label.upper(), 10, color=colors.INK_LIGHT, weight=ft.FontWeight.W_700), text(value, 20, color=colors.HOUSE_GREEN, weight=ft.FontWeight.W_700)], spacing=3),
        padding=12,
        radius=16,
        expand=True,
    )


def positioned(data) -> list[tuple[int, dict]]:
    """Rows in display order; equal points share the same rank."""
    ranked = sorted(data, key=lambda row: (-int(row["points"]), str(row["name"]).casefold()))
    rows: list[tuple[int, dict]] = []
    last, position = None, 0
    for index, row in enumerate(ranked, 1):
        if int(row["points"]) != last:
            position = index
        last = int(row["points"])
        rows.append((position, row))
    return rows


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
        panel = ft.Column(
            [section_title(title), ft.ProgressBar()],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
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
        controls = self.profile(panel, data) if kind == "profile" else self.ranking(data)
        controls.append(
            ft.Row(
                [self.app.pill("Refresh", lambda _: self.open(kind, force=True), primary=False)],
                alignment=ft.MainAxisAlignment.CENTER,
            )
        )
        panel.controls = controls
        panel.update()

    def ranking(self, data) -> list[ft.Control]:
        """Podium for the top three, plain rows for the rest."""
        rows = positioned(data)
        controls = [section_title("Leaderboard", "Each player’s best completed two-level run.")]
        if not rows:
            controls.append(
                surface(
                    ft.Column(
                        [
                            ft.Icon(ft.Icons.LEADERBOARD_OUTLINED, color=colors.GOLD, size=32),
                            text("No runs on the board yet", 17, color=colors.HOUSE_GREEN, weight=ft.FontWeight.W_700),
                            text("Complete both levels in one run to post the first score.", 13, color=colors.INK_LIGHT, text_align=ft.TextAlign.CENTER),
                        ],
                        spacing=8,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    fill=colors.GOLD_SURFACE,
                    padding=22,
                )
            )
            return controls

        top = rows[:3]
        heights = (86, 64, 50)
        steps = [podium_step(row, heights[index], champion=(index == 0)) for index, (_, row) in enumerate(top)]
        # Visual order 2 - 1 - 3 so the winner sits highest in the middle.
        ordered = [steps[1], steps[0], steps[2]] if len(steps) == 3 else steps
        controls.append(
            ft.Container(
                ft.Column(
                    [
                        ft.Row(ordered, vertical_alignment=ft.CrossAxisAlignment.END, spacing=8),
                        text("Top run · 200 points possible", 11, color="#b7d7ca", text_align=ft.TextAlign.CENTER),
                    ],
                    spacing=10,
                ),
                bgcolor=colors.HOUSE_GREEN,
                border_radius=22,
                padding=ft.Padding.only(left=14, right=14, top=16, bottom=14),
            )
        )
        rest = rows[3:]
        if rest:
            controls.append(ft.Column([rank_row(place, row) for place, row in rest], spacing=8))
        return controls

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
            section_title("Profile", "Your record across both levels."),
            self.identity_card(data, best),
            ft.Row(
                [
                    metric("Attempts", str(data["attempts"])),
                    metric("Levels passed", str(data["passed"])),
                    metric("Best run", f"{best}/200" if best is not None else "—"),
                ],
                spacing=8,
            ),
            self.history_card(data),
        ]
        controls.extend(self.account_card(panel, data))
        return controls

    def identity_card(self, data, best) -> ft.Control:
        return surface(
            ft.Row(
                [
                    ft.Container(
                        text(initials_of(data["name"]), 17, color=colors.HOUSE_GREEN, weight=ft.FontWeight.W_700),
                        width=56,
                        height=56,
                        bgcolor=colors.GOLD_SURFACE,
                        border=ft.Border.all(2, colors.GOLD),
                        border_radius=28,
                        alignment=ft.Alignment(0, 0),
                    ),
                    ft.Column(
                        [
                            text(str(data["name"]), 18, color=colors.HOUSE_GREEN, weight=ft.FontWeight.W_700, max_lines=1),
                            text("Guest player" if data["kind"] == "guest" else "Player account", 12, color=colors.INK_LIGHT),
                            ft.Container(
                                text(rank_of(best), 10, color="#8a6a22", weight=ft.FontWeight.W_700),
                                bgcolor=colors.GOLD_SURFACE,
                                border=ft.Border.all(1, colors.GOLD),
                                border_radius=20,
                                padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                            ),
                        ],
                        spacing=4,
                        expand=True,
                    ),
                ],
                spacing=14,
            ),
            padding=16,
        )

    def history_card(self, data) -> ft.Control:
        rows = data["history"][:5]
        children: list[ft.Control] = [text("Recent attempts", 15, color=colors.HOUSE_GREEN, weight=ft.FontWeight.W_700)]
        if not rows:
            children.append(text("Your next result will appear here.", 13, color=colors.INK_LIGHT))
        for row in rows:
            passed = not row["failed"]
            children.append(
                ft.Row(
                    [
                        ft.Container(width=7, height=7, bgcolor=colors.GREEN_ACCENT if passed else colors.ERROR, border_radius=4),
                        text(f'Level {row["level"]}', 13, color=colors.INK, weight=ft.FontWeight.W_700),
                        text("Passed" if passed else "Time out", 11, color=colors.GREEN_ACCENT if passed else colors.ERROR),
                        ft.Container(expand=True),
                        text(str(row["date"])[:10], 10, color=colors.INK_LIGHT),
                        ft.Container(
                            text(f'{row["points"]}/100', 11, color=colors.HOUSE_GREEN, weight=ft.FontWeight.W_700),
                            bgcolor=colors.NEUTRAL_WARM,
                            border_radius=20,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                        ),
                    ],
                    spacing=7,
                )
            )
        return surface(ft.Column(children, spacing=10), padding=16)

    def account_card(self, panel, data) -> list[ft.Control]:
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

            fields = [
                name,
                self.app.pill("Create account with my guest history", register),
                code,
                self.app.pill("Sign in", login, primary=False),
            ]
        else:
            key = ft.TextField(
                label="Private sign-in code · save to sign in on another device",
                value=self.client.identity["key"],
                password=True,
                can_reveal_password=True,
                read_only=True,
            )

            async def logout(_):
                await submit(self.client.sign_out)

            fields = [key, self.app.pill("Sign out and play as guest", logout, primary=False)]
        return [
            surface(
                ft.Column(
                    [text("Account", 15, color=colors.HOUSE_GREEN, weight=ft.FontWeight.W_700), *fields, message],
                    spacing=12,
                ),
                padding=16,
            )
        ]
        return controls
