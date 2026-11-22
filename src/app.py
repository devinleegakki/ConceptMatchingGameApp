import asyncio
import os
from dataclasses import dataclass

import flet as ft

from components.game_card import game_card
from models.card import LevelData
from services.csv_loader import DataError, load_level
from services.game_engine import GameEngine
from theme import colors

DEFAULT_CSV_URL = "https://docs.google.com/spreadsheets/d/1f055xrnz5R1XLxFZ6zxACPGBSYEZ_4s-ee0GUERpTC4/export?format=csv"


@dataclass
class Score:
    level: int
    steps: int
    remaining_seconds: int
    max_combo: int
    failed: bool


class App:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "概念配对挑战"
        self.page.bgcolor = colors.CANVAS
        self.page.padding = 0
        self.page.theme = ft.Theme(font_family="Arial")
        self.csv_url = os.getenv("CSV_URL", DEFAULT_CSV_URL)
        self.engine: GameEngine | None = None
        self.level_data: LevelData | None = None
        self.level = 1
        self.scores: list[Score] = []
        self.message = ""
        self.loading = False
        self.show_home()

    def shell(self, content: ft.Control) -> ft.Control:
        return ft.Column(
            [
                ft.Container(ft.Text("CONCEPT MATCHING // STUDY MODE", color=colors.NAV_GOLD, weight=ft.FontWeight.BOLD, size=12), bgcolor=colors.CARBON, padding=10),
                ft.Container(content, padding=16, expand=True),
            ],
            expand=True,
            spacing=0,
        )

    def show_home(self, error: str | None = None):
        self.page.clean()
        warning = ft.Container(ft.Text(error, color=colors.SURFACE), bgcolor=colors.ERROR, padding=10, visible=bool(error))
        content = ft.Column(
            [
                ft.Container(ft.Text("概念配对", size=42, weight=ft.FontWeight.BOLD, color=colors.SURFACE), bgcolor=colors.LAVENDER if hasattr(colors, "LAVENDER") else colors.PERIWINKLE, padding=20, border_radius=6),
                ft.Text("拖动两张相关卡片到中央配对区，建立知识联结。", size=16, color=colors.INK),
                warning,
                ft.FilledButton("开始挑战", bgcolor=colors.AMBER, color=colors.CARBON, on_click=lambda _: self.start_level(1)),
                ft.Text("第一关 4 对卡片 · 第二关 6 对卡片", size=12, color=colors.CHROME_INDIGO),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=18,
        )
        self.page.add(self.shell(content))
        self.page.update()

    async def load_and_start(self, level: int):
        self.loading = True
        self.page.update()
        try:
            self.level_data = await asyncio.to_thread(load_level, self.csv_url, level)
        except DataError as exc:
            self.loading = False
            self.show_home(str(exc))
            return
        self.loading = False
        self.level = level
        self.engine = GameEngine(self.level_data)
        self.show_game()
        self.page.run_task(self.timer_loop)

    def start_level(self, level: int):
        if self.loading:
            return
        self.page.run_task(self.load_and_start, level)

    def timer_loop(self):
        async def loop():
            while self.engine and not self.engine.state.is_finished:
                await asyncio.sleep(1)
                if self.engine and self.engine.tick():
                    self.refresh_game()
                    if self.engine.state.is_finished:
                        await self.finish_level()
        return loop()

    def on_card(self, card_id: str):
        if not self.engine:
            return
        result = self.engine.select(card_id)
        self.refresh_game()
        if result == "mismatch":
            self.page.run_task(self.resolve_mismatch)
        elif result == "matched" and self.engine.state.is_finished:
            self.page.run_task(self.finish_level)

    async def resolve_mismatch(self):
        await asyncio.sleep(0.7)
        if self.engine:
            self.engine.resolve_mismatch()
            self.refresh_game()

    async def finish_level(self):
        await asyncio.sleep(0.35)
        if not self.engine:
            return
        state = self.engine.state
        if not any(score.level == state.level for score in self.scores):
            self.scores.append(Score(state.level, state.steps, state.remaining_seconds, state.max_combo, state.is_failed))
        self.show_level_result()

    def refresh_game(self):
        self.show_game()

    def show_game(self):
        if not self.engine:
            return
        state = self.engine.state
        cards = [game_card(card, self.on_card) for card in state.cards]
        selected = ", ".join(state.selected_card_ids) if state.selected_card_ids else "等待第二张卡"
        target = ft.DragTarget(
            group="cards",
            on_accept=lambda event: self.on_card(event.data),
            content=ft.Container(
                ft.Column([ft.Text("配对区域", size=18, weight=ft.FontWeight.BOLD, color=colors.CARBON), ft.Text(selected, size=12, color=colors.CHROME_INDIGO)], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=colors.AMBER if state.selected_card_ids else colors.CANVAS_SOFT,
                border=ft.Border.all(2, colors.SIGNAL),
                border_radius=6,
                padding=14,
                height=92,
                alignment=ft.Alignment(0, 0),
            ),
        )
        grid = ft.GridView(expand=True, max_extent=170, runs_count=2, spacing=10, run_spacing=10)
        grid.controls = cards
        hud = ft.Row([
            ft.Text(f"LEVEL {state.level}", color=colors.SURFACE, weight=ft.FontWeight.BOLD),
            ft.Text(f"时间 {state.remaining_seconds}s", color=colors.SURFACE),
            ft.Text(f"步数 {state.steps}", color=colors.SURFACE),
            ft.Text(f"连击 ×{state.combo}", color=colors.NAV_GOLD, weight=ft.FontWeight.BOLD),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        content = ft.Column([ft.Container(hud, bgcolor=colors.CARBON, padding=10), target, grid], expand=True, spacing=12)
        self.page.clean()
        self.page.add(self.shell(content))
        self.page.update()

    def show_level_result(self):
        if not self.engine:
            return
        state = self.engine.state
        content = ft.Column([
            ft.Text("本关结算", size=32, weight=ft.FontWeight.BOLD, color=colors.SURFACE),
            ft.Text("挑战完成" if not state.is_failed else "时间到", size=20, color=colors.INK),
            ft.Text(f"步数：{state.steps}"),
            ft.Text(f"剩余时间：{state.remaining_seconds} 秒"),
            ft.Text(f"最高连击：×{state.max_combo}"),
            ft.FilledButton("进入第二关" if state.level == 1 else "查看总成绩", bgcolor=colors.SIGNAL, color=colors.SURFACE, on_click=lambda _: self.start_level(2) if state.level == 1 else self.show_summary()),
            ft.TextButton("返回首页", on_click=lambda _: self.show_home()),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, spacing=14)
        self.page.clean(); self.page.add(self.shell(content)); self.page.update()

    def show_summary(self):
        rows = [ft.Text(f"第 {score.level} 关：步数 {score.steps} · 剩余 {score.remaining_seconds}s · 最高连击 ×{score.max_combo}") for score in self.scores]
        content = ft.Column([
            ft.Text("汇总结算", size=32, weight=ft.FontWeight.BOLD, color=colors.SURFACE),
            *rows,
            ft.FilledButton("重新挑战", bgcolor=colors.AMBER, color=colors.CARBON, on_click=lambda _: self.restart()),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, spacing=14)
        self.page.clean(); self.page.add(self.shell(content)); self.page.update()

    def restart(self):
        self.scores.clear()
        self.start_level(1)


def main(page: ft.Page):
    App(page)

