import asyncio
import os
from dataclasses import dataclass

import flet as ft

from components.game_card import game_card
from models.card import LevelData
from services.csv_loader import DataError, load_level
from services.game_engine import GameEngine
from theme import colors, typography
from theme.styles import dark_button, primary_button, secondary_button

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
        self.page.title = "概念配对 · Concept Match"
        self.page.bgcolor = colors.NEUTRAL_WARM
        self.page.padding = 0
        self.page.theme = ft.Theme(font_family=typography.FONT_FAMILY)
        self.csv_url = os.getenv("CSV_URL", DEFAULT_CSV_URL)
        self.engine: GameEngine | None = None
        self.level_data: LevelData | None = None
        self.scores: list[Score] = []
        self.loading = False
        self.show_home()

    def top_bar(self, dark: bool = False) -> ft.Control:
        bg = colors.BLACK if dark else colors.HOUSE_GREEN
        fg = colors.WHITE
        return ft.Container(
            ft.Row(
                [
                    ft.Text("CONCEPT MATCH", size=14, weight=ft.FontWeight.W_600, color=fg, font_family=typography.FONT_FAMILY),
                    ft.Text("学习配对", size=12, color="#B7D7CA", font_family=typography.FONT_FAMILY),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            bgcolor=bg,
            padding=ft.Padding.symmetric(horizontal=20, vertical=14),
        )

    def pill(self, label: str, on_click, *, primary: bool = True, dark: bool = False) -> ft.Control:
        return ft.FilledButton(
            label,
            on_click=on_click,
            style=dark_button() if dark else primary_button() if primary else secondary_button(),
            height=48,
        )

    def shell(self, content: ft.Control, *, dark: bool = False) -> ft.Control:
        return ft.Column([self.top_bar(dark), ft.Container(content, padding=20, expand=True)], expand=True, spacing=0)

    def show_home(self, error: str | None = None):
        self.page.clean()
        error_view = ft.Container(
            ft.Row([ft.Icon(ft.Icons.ERROR_OUTLINE, color=colors.ERROR), ft.Text(error or "", color=colors.ERROR, size=14, expand=True)]),
            bgcolor="#0dc820140d",
            border=ft.Border.all(1, colors.ERROR),
            border_radius=12,
            padding=14,
            visible=bool(error),
        )
        hero = ft.Container(
            ft.Column(
                [
                    ft.Text("概念配对", size=40, weight=ft.FontWeight.W_600, color=colors.WHITE, font_family=typography.FONT_FAMILY),
                    ft.Text("CONCEPT MATCH", size=14, color="#B7D7CA", font_family=typography.FONT_FAMILY),
                    ft.Container(height=8),
                    ft.Text("把题目和公式重新连起来。", size=20, color=colors.WHITE, font_family=typography.FONT_FAMILY),
                    ft.Text("所有卡片都会直接显示信息，你只需要根据概念完成配对。", size=15, color="#D9E8E2", font_family=typography.FONT_FAMILY),
                    ft.Container(height=8),
                    ft.Row([self.pill("开始挑战", lambda _: self.start_level(1)), self.pill("玩法说明", lambda _: self.show_instructions(), primary=False)], spacing=10),
                ], spacing=10,
            ),
            bgcolor=colors.HOUSE_GREEN,
            border_radius=18,
            padding=28,
        )
        stats = ft.Row([
            self.info_tile("第 1 关", "4 对卡片"),
            self.info_tile("第 2 关", "6 对卡片"),
            self.info_tile("目标", "建立联结"),
        ], spacing=12)
        content = ft.Column([hero, error_view, ft.Text("挑战概览", size=24, weight=ft.FontWeight.W_600, color=colors.STARBUCKS_GREEN), stats], spacing=18, scroll=ft.ScrollMode.AUTO)
        self.page.add(self.shell(content)); self.page.update()

    def info_tile(self, title: str, value: str) -> ft.Control:
        return ft.Container(ft.Column([ft.Text(title, size=14, color=colors.INK_LIGHT), ft.Text(value, size=17, weight=ft.FontWeight.W_600, color=colors.INK)], spacing=4), bgcolor=colors.WHITE, border_radius=12, padding=16, expand=True)

    def show_instructions(self):
        self.page.clean()
        content = ft.Column([
            ft.Text("怎么玩", size=34, weight=ft.FontWeight.W_600, color=colors.STARBUCKS_GREEN),
            ft.Text("选择一张题目卡，再选择对应的公式卡。也可以拖动卡片到中央配对区。", size=17, color=colors.INK),
            ft.Container(ft.Column([ft.Text("配对规则", size=20, weight=ft.FontWeight.W_600, color=colors.STARBUCKS_GREEN), ft.Text("正确配对会增加连击；错误配对会短暂锁定操作。计时、步数和最高连击会记录在结算页。", size=16, color=colors.INK)], spacing=8), bgcolor=colors.WHITE, border_radius=12, padding=20),
            self.pill("返回首页", lambda _: self.show_home(), primary=False),
        ], spacing=18, scroll=ft.ScrollMode.AUTO)
        self.page.add(self.shell(content)); self.page.update()

    async def load_and_start(self, level: int):
        self.loading = True
        try:
            self.level_data = await asyncio.to_thread(load_level, self.csv_url, level)
        except DataError as exc:
            self.loading = False; self.show_home(str(exc)); return
        self.loading = False
        self.engine = GameEngine(self.level_data)
        self.show_game()
        self.page.run_task(self.timer_loop, self.engine)

    def start_level(self, level: int):
        if not self.loading:
            self.page.run_task(self.load_and_start, level)

    async def timer_loop(self, engine: GameEngine):
        while self.engine is engine and not engine.state.is_finished:
            await asyncio.sleep(1)
            if self.engine is not engine: return
            if engine.tick():
                self.refresh_game()
                if engine.state.is_finished: await self.finish_level()

    def on_card(self, card_id: str):
        if not self.engine: return
        result = self.engine.select(card_id); self.refresh_game()
        if result == "mismatch": self.page.run_task(self.resolve_mismatch)
        elif result == "matched" and self.engine.state.is_finished: self.page.run_task(self.finish_level)

    async def resolve_mismatch(self):
        await asyncio.sleep(0.7)
        if self.engine: self.engine.resolve_mismatch(); self.refresh_game()

    async def finish_level(self):
        await asyncio.sleep(0.35)
        if not self.engine: return
        state = self.engine.state
        if not any(score.level == state.level for score in self.scores): self.scores.append(Score(state.level, state.steps, state.remaining_seconds, state.max_combo, state.is_failed))
        self.show_level_result()

    def refresh_game(self): self.show_game()

    def show_game(self):
        if not self.engine: return
        state = self.engine.state
        duration = self.level_data.duration_seconds if self.level_data else max(1, state.remaining_seconds)
        progress = max(0.0, min(1.0, 1 - state.remaining_seconds / duration))
        cards = [game_card(card, self.on_card, selected=card.id in state.selected_card_ids, width=78, height=132) for card in state.cards]
        target = ft.DragTarget(group="cards", on_accept=lambda event: self.on_card(event.data), content=ft.Container(ft.Column([ft.Text("配对区", size=18, weight=ft.FontWeight.W_600, color=colors.HOUSE_GREEN), ft.Text("选择题目 + 公式", size=13, color=colors.INK_LIGHT)], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4), bgcolor=colors.WHITE, border=ft.Border.all(1, colors.GREEN_LIGHT), border_radius=18, padding=14, height=82, alignment=ft.Alignment(0, 0)))
        grid = ft.GridView(expand=True, runs_count=4, max_extent=96, spacing=8, run_spacing=10, child_aspect_ratio=0.59)
        grid.controls = cards
        hud = ft.Row([ft.Text(f"LEVEL {state.level}", color=colors.WHITE, weight=ft.FontWeight.W_600, size=13), ft.Text(f"步数 {state.steps}", color=colors.WHITE, size=13), ft.Text(f"连击 ×{state.combo}", color=colors.WHITE, size=13), ft.Text(f"{state.remaining_seconds}s", color=colors.WHITE, weight=ft.FontWeight.W_600, size=13)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        countdown = ft.ProgressBar(value=progress, bar_height=8, color=colors.GREEN_LIGHT, bgcolor=colors.GREEN_UPLIFT, border_radius=8, semantics_label="关卡倒计时进度", semantics_value=f"{state.remaining_seconds}秒剩余")
        hint = ft.Text("卡片内容已显示，请完成配对" if not state.is_locked else "配对错误，请稍候再试", color="#D9E8E2" if not state.is_locked else "#F4B5AE", size=14)
        content = ft.Column([ft.Container(ft.Column([hud, countdown, hint], spacing=10), bgcolor=colors.HOUSE_GREEN, border_radius=18, padding=16), target, grid], expand=True, spacing=16, scroll=ft.ScrollMode.AUTO)
        self.page.clean(); self.page.add(self.shell(content, dark=True)); self.page.update()

    def show_level_result(self):
        if not self.engine: return
        state = self.engine.state
        content = ft.Column([
            ft.Text("本关结算", size=34, weight=ft.FontWeight.W_600, color=colors.STARBUCKS_GREEN),
            ft.Text("挑战完成" if not state.is_failed else "时间到", size=20, color=colors.ERROR if state.is_failed else colors.INK),
            ft.Row([self.info_tile("步数", str(state.steps)), self.info_tile("剩余时间", f"{state.remaining_seconds}s"), self.info_tile("最高连击", f"×{state.max_combo}")], spacing=10),
            self.pill("进入第二关" if state.level == 1 else "查看总成绩", lambda _: self.start_level(2) if state.level == 1 else self.show_summary()),
            self.pill("返回首页", lambda _: self.show_home(), primary=False),
        ], spacing=18, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO)
        self.page.clean(); self.page.add(self.shell(content)); self.page.update()

    def show_summary(self):
        rows = [ft.Container(ft.Row([ft.Text(f"第 {score.level} 关", weight=ft.FontWeight.W_600, color=colors.STARBUCKS_GREEN), ft.Text(f"{score.steps} 步 · {score.remaining_seconds}s · 连击 ×{score.max_combo}", color=colors.INK_MUTED)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), bgcolor=colors.WHITE, border_radius=12, padding=16) for score in self.scores]
        content = ft.Column([ft.Text("汇总结算", size=34, weight=ft.FontWeight.W_600, color=colors.STARBUCKS_GREEN), ft.Text("你的概念联结记录", size=17, color=colors.INK), *rows, self.pill("重新挑战", lambda _: self.restart()), self.pill("返回首页", lambda _: self.show_home(), primary=False)], spacing=16, scroll=ft.ScrollMode.AUTO)
        self.page.clean(); self.page.add(self.shell(content)); self.page.update()

    def restart(self):
        self.scores.clear(); self.start_level(1)


def main(page: ft.Page):
    App(page)
