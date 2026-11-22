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
IPHONE_17_PRO_MAX_WIDTH = 440
IPHONE_17_PRO_MAX_HEIGHT = 956


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
        self.is_web_preview = bool(getattr(page, "web", False))
        self.page.bgcolor = "#d9d5ce" if self.is_web_preview else colors.NEUTRAL_WARM
        self.page.padding = 0
        self.page.theme = ft.Theme(font_family=typography.FONT_FAMILY)
        self.csv_url = os.getenv("CSV_URL", DEFAULT_CSV_URL)
        self.engine: GameEngine | None = None
        self.level_data: LevelData | None = None
        self.scores: list[Score] = []
        self.loading = False
        self.pair_zone_hover = False
        self.pair_hover_slot: int | None = None
        self.pair_slots = [None, None]
        self.pair_zone_visuals: list[ft.Container] = []
        self.feedback_status: str | None = None
        self.feedback_cards = []
        self.feedback_explanation: str | None = None
        self._web_connected = True
        if self.is_web_preview:
            self.page.on_connect = self._on_web_connect
            self.page.on_disconnect = self._on_web_disconnect
        self.show_home()

    def _on_web_connect(self, _event):
        # A refresh/reconnect within the grace period keeps the dev server alive.
        self._web_connected = True

    def _on_web_disconnect(self, _event):
        self._web_connected = False
        self.page.run_task(self._exit_after_disconnect)

    async def _exit_after_disconnect(self):
        # Flet sends disconnect before a browser refresh can reconnect. Keep a
        # small grace period so normal reloads do not kill the terminal.
        await asyncio.sleep(1.5)
        if not self._web_connected:
            os._exit(0)

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
        app_surface = ft.Column([self.top_bar(dark), ft.Container(content, padding=20, expand=True)], expand=True, spacing=0)
        if not self.is_web_preview:
            return app_surface
        # Keep browser previews at the logical iPhone 17 Pro Max viewport even
        # when the browser window is a wide desktop rectangle.
        device = ft.Container(
            app_surface,
            width=IPHONE_17_PRO_MAX_WIDTH,
            height=IPHONE_17_PRO_MAX_HEIGHT,
            bgcolor=colors.NEUTRAL_WARM,
            border_radius=28,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            shadow=ft.BoxShadow(blur_radius=24, spread_radius=2, color="#52000000", offset=ft.Offset(0, 8)),
        )
        return ft.Row([device], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER, expand=True)

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
            ft.Text("将两张卡片依次拖到下方配对区，系统会自动判断。", size=17, color=colors.INK),
            ft.Container(ft.Column([ft.Text("配对规则", size=20, weight=ft.FontWeight.W_600, color=colors.STARBUCKS_GREEN), ft.Text("先拖入题目或公式，再拖入对应卡片。正确配对会增加连击；错误配对会短暂锁定操作。", size=16, color=colors.INK)], spacing=8), bgcolor=colors.WHITE, border_radius=12, padding=20),
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
        self.feedback_status = None
        self.feedback_cards = []
        self.feedback_explanation = None
        self.pair_zone_hover = False
        self.pair_hover_slot = None
        self.pair_slots = [None, None]
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
        if not self.engine or self.feedback_status or card_id is None:
            return
        # The pointer has left the drop target once a card is released.
        self.pair_zone_hover = False
        self.pair_hover_slot = None
        card_id = str(card_id)
        candidate = self.engine.card(card_id)
        if candidate is None:
            return
        selected_before = list(self.engine.state.selected_card_ids)
        # Keep immutable display snapshots before the engine marks a successful
        # pair as matched. The feedback UI must show both cards during the
        # 700ms confirmation window.
        first_snapshot = self.engine.card(selected_before[0]) if selected_before else None
        second_snapshot = candidate
        result = self.engine.select(card_id)
        if result == "mismatch":
            self.feedback_status = "error"
            # A new completed attempt replaces the previous explanation.
            self.feedback_explanation = None
            self.feedback_cards = [self.engine.card(item_id) for item_id in selected_before + [card_id]]
            self.feedback_cards = [card for card in self.feedback_cards if card is not None]
            self.pair_slots = list(self.feedback_cards[:2]) + [None, None]
            self.pair_slots = self.pair_slots[:2]
            self.refresh_game()
            self.page.run_task(self.resolve_feedback)
        elif result == "matched":
            self.feedback_status = "success"
            self.feedback_cards = [card for card in (first_snapshot, second_snapshot) if card is not None]
            self.pair_slots = list(self.feedback_cards[:2]) + [None, None]
            self.pair_slots = self.pair_slots[:2]
            question_explanations = [card.explanation for card in self.feedback_cards if card.type == "question" and card.explanation]
            self.feedback_explanation = question_explanations[0] if question_explanations else next((card.explanation for card in self.feedback_cards if card.explanation), None)
            # Successful pairs are also locked during the 700ms feedback.
            self.engine.state.is_locked = True
            self.refresh_game()
            self.page.run_task(self.resolve_feedback)
        else:
            self.pair_slots[0] = candidate
            self.refresh_game()

    def pair_zone_accepts(self, event) -> bool:
        """Validate a drag before Flet treats the drop zone as active."""
        card_id = self.drag_card_id(event)
        if not card_id or not self.engine or self.feedback_status:
            return False
        card = self.engine.card(card_id)
        return card is not None and not card.is_matched and card_id not in self.engine.state.selected_card_ids and not self.engine.state.is_locked

    def pair_zone_will_accept(self, event, slot_index: int) -> bool:
        accepted = self.pair_zone_accepts(event)
        self.pair_zone_hover = accepted
        self.pair_hover_slot = slot_index if accepted else None
        self.update_pair_zone_visuals()
        # Do not rebuild the page from inside Flet's hit-test callback. A
        # rebuild here invalidates the active drag target and causes the card
        # to snap back, especially on the third row of level two.
        return accepted

    def pair_zone_leave(self, _event, slot_index: int):
        if self.pair_hover_slot == slot_index:
            self.pair_zone_hover = False
            self.pair_hover_slot = None
            self.update_pair_zone_visuals()

    def update_pair_zone_visuals(self):
        if not self.pair_zone_visuals:
            return
        for index, visual in enumerate(self.pair_zone_visuals):
            occupied = self.pair_slots[index] is not None
            is_hovered = self.pair_zone_hover and self.pair_hover_slot == index
            if self.feedback_status == "success":
                background, border = colors.GREEN_LIGHT, colors.GREEN_ACCENT
            elif self.feedback_status == "error":
                background, border = "#fbe9e7", colors.ERROR
            elif is_hovered or occupied:
                background, border = colors.GREEN_LIGHT, colors.GREEN_ACCENT
            else:
                background, border = colors.WHITE, colors.HAIRLINE
            visual.bgcolor = background
            visual.border = ft.Border.all(2 if is_hovered or occupied or self.feedback_status else 1, border)
            try:
                visual.update()
            except RuntimeError:
                # Initial construction happens before the control is attached;
                # the assigned properties will be sent with the page update.
                pass

    @staticmethod
    def drag_card_id(event) -> str | None:
        """Read drag data across Flet web/desktop event representations."""
        data = getattr(event, "data", None)
        if data is None:
            source = getattr(event, "src", None)
            data = getattr(source, "data", None)
        if data is None:
            return None
        return str(data)

    async def resolve_feedback(self):
        await asyncio.sleep(0.7)
        if not self.engine:
            return
        was_success = self.feedback_status == "success"
        if not was_success:
            self.engine.resolve_mismatch()
            # An incorrect next attempt ends the previous explanation's
            # lifetime as well.
            self.feedback_explanation = None
        else:
            self.engine.state.is_locked = False
        self.feedback_status = None
        self.feedback_cards = []
        self.pair_slots = [None, None]
        self.pair_zone_hover = False
        self.pair_hover_slot = None
        if was_success and self.engine.state.is_finished:
            self.show_level_result()
        else:
            self.refresh_game()

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
        selected_ids = {card.id for card in self.pair_slots if card is not None}
        feedback_ids = {card.id for card in self.feedback_cards}
        available_cards = [card for card in state.cards if card.id not in selected_ids and card.id not in feedback_ids]
        cards = [game_card(card, selected=False, width=78, height=132) for card in available_cards]
        self.pair_zone_visuals = []
        targets = []
        for slot_index in range(2):
            slot_card = self.pair_slots[slot_index]
            slot_content = game_card(slot_card, selected=True, draggable=False, width=128, height=104) if slot_card else ft.Text("拖入卡片" if slot_index == 0 else "第二张卡", size=13, color=colors.INK_LIGHT)
            target_visual = ft.Container(
                ft.Column([ft.Text("左区" if slot_index == 0 else "右区", size=16, weight=ft.FontWeight.W_600, color=colors.HOUSE_GREEN), slot_content], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                bgcolor=colors.WHITE,
                border=ft.Border.all(1, colors.HAIRLINE),
                border_radius=18,
                padding=12,
                height=150,
                width=190,
                alignment=ft.Alignment(0, 0),
            )
            self.pair_zone_visuals.append(target_visual)
            targets.append(ft.DragTarget(group="cards", on_will_accept=lambda event, i=slot_index: self.pair_zone_will_accept(event, i), on_accept=lambda event: self.on_card(self.drag_card_id(event)), on_leave=lambda event, i=slot_index: self.pair_zone_leave(event, i), content=target_visual))
        self.update_pair_zone_visuals()
        target = ft.Row(targets, alignment=ft.MainAxisAlignment.CENTER, spacing=10)
        # Build rows explicitly instead of relying on GridView's aspect-ratio
        # calculation. This keeps the visual cards and their hit regions from
        # extending into the pairing target below.
        card_rows = [
            ft.Row(cards[index:index + 4], alignment=ft.MainAxisAlignment.CENTER, spacing=8)
            for index in range(0, len(cards), 4)
        ]
        grid = ft.Column(card_rows, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)
        hud = ft.Row([ft.Text(f"LEVEL {state.level}", color=colors.WHITE, weight=ft.FontWeight.W_600, size=13), ft.Text(f"步数 {state.steps}", color=colors.WHITE, size=13), ft.Text(f"连击 ×{state.combo}", color=colors.WHITE, size=13), ft.Text(f"{state.remaining_seconds}s", color=colors.WHITE, weight=ft.FontWeight.W_600, size=13)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        countdown = ft.ProgressBar(value=progress, bar_height=8, color=colors.GREEN_LIGHT, bgcolor=colors.GREEN_UPLIFT, border_radius=8, semantics_label="关卡倒计时进度", semantics_value=f"{state.remaining_seconds}秒剩余")
        if self.feedback_status == "success":
            hint_text, hint_color = "配对成功", colors.GREEN_LIGHT
        elif self.feedback_status == "error":
            hint_text, hint_color = "配对不正确，请稍候再试", "#F4B5AE"
        else:
            hint_text, hint_color = "拖动两张卡片到下方配对区", "#D9E8E2"
        hint = ft.Text(hint_text, color=hint_color, size=14)
        explanation_view = ft.Container(
            ft.Text(f"解释：{self.feedback_explanation}", size=14, color=colors.INK, text_align=ft.TextAlign.CENTER),
            bgcolor=colors.WHITE,
            border_radius=12,
            padding=12,
            # Keep the last successful explanation visible while the next
            # pair is being considered; it is replaced/cleared on completion
            # of that next attempt.
            visible=bool(self.feedback_explanation),
        )
        content = ft.Column([ft.Container(ft.Column([hud, countdown, hint], spacing=10), bgcolor=colors.HOUSE_GREEN, border_radius=18, padding=16), grid, target, explanation_view], expand=True, spacing=16, scroll=ft.ScrollMode.AUTO)
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
