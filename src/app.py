import asyncio
import os
from dataclasses import dataclass

import flet as ft

from components.game_card import game_card
from components.design_system import badge, button, combo_badge, concept_node, hero_visual, illustration_card, pager_title_block, progress_ring, section_title, stat_card, surface, text
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
        self.page.title = "Concept Match"
        self.is_web_preview = bool(getattr(page, "web", False))
        self.page.bgcolor = "#d9d5ce" if self.is_web_preview else colors.NEUTRAL_WARM
        self.page.padding = 0
        self.page.theme = ft.Theme(
            font_family=typography.FONT_FAMILY,
            navigation_bar_theme=ft.NavigationBarTheme(
                label_text_style={
                    ft.ControlState.SELECTED: ft.TextStyle(color=colors.HOUSE_GREEN, size=12, weight=ft.FontWeight.W_700),
                    ft.ControlState.DEFAULT: ft.TextStyle(color=colors.INK_LIGHT, size=12, weight=ft.FontWeight.W_500),
                },
                indicator_color=colors.GOLD_SURFACE,
                overlay_color={ft.ControlState.SELECTED: colors.GOLD_SURFACE, ft.ControlState.DEFAULT: colors.CERAMIC},
            ),
        )
        self.csv_url = os.getenv("CSV_URL", DEFAULT_CSV_URL)
        self.engine: GameEngine | None = None
        self.level_data: LevelData | None = None
        self.scores: list[Score] = []
        self.loading = False
        self.pair_zone_hover = False
        self.pair_hover_slot: int | None = None
        self.pair_slots = [None, None]
        self.pair_locked_type: str | None = None
        self.pair_zone_visuals: list[ft.Container] = []
        self.pair_workspace_visual: ft.Container | None = None
        self.game_timer_text: ft.Text | None = None
        self.combo_badge: ft.Container | None = None
        self.game_countdown: ft.ProgressBar | None = None
        self.pair_hover_card_id: str | None = None
        self.feedback_status: str | None = None
        self.feedback_cards = []
        self.feedback_explanation: str | None = None
        self.home_page_index = 0
        self.home_pager: ft.PageView | None = None
        self.home_page_dots: list[ft.Container] = []
        self.leaderboard_entries: list[dict] = []
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
        session = getattr(self.page, "session", None)
        if session is None or getattr(getattr(session, "connection", None), "loop", None) is None:
            return
        self.page.run_task(self._exit_after_disconnect)

    async def _exit_after_disconnect(self):
        # Flet sends disconnect before a browser refresh can reconnect. Keep a
        # small grace period so normal reloads do not kill the terminal.
        await asyncio.sleep(1.5)
        if not self._web_connected:
            os._exit(0)

    def top_bar(self, dark: bool = False) -> ft.Control:
        bg = colors.HOUSE_GREEN if dark else colors.WHITE
        fg = colors.WHITE
        return ft.Container(
            ft.Row(
                [
                    ft.Row([ft.Container(width=10, height=10, bgcolor=colors.GOLD, border_radius=10), ft.Text("CONCEPT MATCH", size=14, weight=ft.FontWeight.W_700, color=fg if dark else colors.HOUSE_GREEN, font_family=typography.FONT_FAMILY)], spacing=8),
                    ft.Text("Pair to learn", size=12, color="#B7D7CA" if dark else colors.INK_LIGHT, font_family=typography.FONT_FAMILY),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            bgcolor=bg,
            padding=ft.Padding.symmetric(horizontal=20, vertical=14),
        )

    def pill(self, label: str, on_click, *, primary: bool = True, dark: bool = False, large: bool = False) -> ft.Control:
        control = button(label, on_click, kind="primary" if primary else "secondary", dark=dark)
        if large:
            control.height = 56
            control.width = 220
        return control

    def shell(self, content: ft.Control, *, dark: bool = False, show_bottom_nav: bool = False, selected_nav: int = 0) -> ft.Control:
        body = ft.Container(content, padding=ft.Padding.symmetric(horizontal=18, vertical=16), alignment=ft.Alignment(0, 0), expand=True)
        controls = [self.top_bar(dark), body]
        if show_bottom_nav:
            controls.append(self.bottom_navigation(selected_nav))
        app_surface = ft.Column(controls, expand=True, spacing=0)
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

    def bottom_navigation(self, selected_index: int) -> ft.NavigationBar:
        return ft.NavigationBar(
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icon(ft.Icons.HOME_OUTLINED, color=colors.INK_LIGHT), selected_icon=ft.Icon(ft.Icons.HOME, color=colors.HOUSE_GREEN), label="Home"),
                ft.NavigationBarDestination(icon=ft.Icon(ft.Icons.LEADERBOARD_OUTLINED, color=colors.INK_LIGHT), selected_icon=ft.Icon(ft.Icons.LEADERBOARD, color=colors.HOUSE_GREEN), label="Leaderboard"),
                ft.NavigationBarDestination(icon=ft.Icon(ft.Icons.PERSON_OUTLINED, color=colors.INK_LIGHT), selected_icon=ft.Icon(ft.Icons.PERSON, color=colors.HOUSE_GREEN), label="Profile"),
            ],
            selected_index=selected_index,
            bgcolor=colors.WHITE,
            indicator_color=colors.GOLD_SURFACE,
            label_behavior=ft.NavigationBarLabelBehavior.ALWAYS_SHOW,
            border=ft.Border(top=ft.BorderSide(1, colors.DIVIDER)),
            on_change=self.on_navigation_change,
        )

    def on_navigation_change(self, event):
        index = int(event.control.selected_index)
        if index == 0:
            self.show_home()
        elif index == 1:
            self.show_leaderboard()
        else:
            self.show_profile()

    def show_home(self, error: str | None = None):
        self.page.clean()
        error_view = ft.Container(
            ft.Row([ft.Icon(ft.Icons.ERROR_OUTLINE, color=colors.ERROR), text(error or "", 14, color=colors.ERROR, max_lines=4)], spacing=10),
            bgcolor=colors.ERROR_SURFACE,
            border=ft.Border.all(1, colors.ERROR),
            border_radius=16,
            padding=14,
            visible=bool(error),
        )
        self.home_page_index = min(max(self.home_page_index, 0), 2)
        dots = [ft.Container(width=7 if index != self.home_page_index else 22, height=7, bgcolor=colors.GOLD if index == self.home_page_index else "#7da194", border_radius=8, animate=ft.Animation(180, ft.AnimationCurve.EASE_OUT)) for index in range(3)]
        self.home_page_dots = dots
        pager = ft.PageView(
            controls=[self.home_concept_page(), self.home_how_to_page(), self.home_progress_page(), self.home_concept_page()],
            selected_index=self.home_page_index,
            height=560,
            expand=True,
            snap=True,
            on_change=lambda event: self.on_home_page_change(event, dots),
        )
        self.home_pager = pager
        pager_container = ft.Container(pager, bgcolor=colors.HOUSE_GREEN, border_radius=26, padding=24, height=610, expand=True, shadow=ft.BoxShadow(blur_radius=18, color="#30001f16", offset=ft.Offset(0, 8)))
        paging_controls = ft.Row([
            ft.IconButton(ft.Icons.CHEVRON_LEFT, tooltip="Previous page", icon_color="#b7d7ca", bgcolor="#2b5148", on_click=lambda _: self.previous_home_page()),
            ft.Row(dots, alignment=ft.MainAxisAlignment.CENTER, spacing=6, expand=True),
            ft.IconButton(ft.Icons.CHEVRON_RIGHT, tooltip="Next page", icon_color="#b7d7ca", bgcolor="#2b5148", on_click=lambda _: self.next_home_page()),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        content = ft.Column([error_view, pager_container, paging_controls], expand=True, spacing=10)
        self.page.add(self.shell(content, show_bottom_nav=True, selected_nav=0)); self.page.update()

    def on_home_page_change(self, event, dots: list[ft.Container]):
        selected_index = int(event.control.selected_index)
        if selected_index == 3:
            self.home_page_index = 0
            event.control.selected_index = 0
            try:
                event.control.update()
            except RuntimeError:
                pass
        else:
            self.home_page_index = selected_index
        self.update_home_page_indicators(dots)

    def go_to_home_page(self, index: int):
        self.home_page_index = index % 3
        if self.home_pager is not None:
            self.home_pager.selected_index = self.home_page_index
            try:
                self.home_pager.update()
            except RuntimeError:
                pass
        self.update_home_page_indicators()

    def next_home_page(self):
        self.go_to_home_page(self.home_page_index + 1)

    def previous_home_page(self):
        self.go_to_home_page(self.home_page_index - 1)

    def update_home_page_indicators(self, dots: list[ft.Container] | None = None):
        dots = dots or self.home_page_dots
        for index, dot in enumerate(dots):
            dot.width = 22 if index == self.home_page_index else 7
            dot.bgcolor = colors.GOLD if index == self.home_page_index else "#7da194"
            try:
                dot.update()
            except RuntimeError:
                pass

    def home_concept_page(self) -> ft.Control:
        visual = hero_visual(ft.Row([
            ft.Column([concept_node(ft.Icons.QUESTION_MARK, size=46, fill=colors.QUESTION_SURFACE, color=colors.GOLD), ft.Container(width=2, height=24, bgcolor="#7da194"), concept_node(ft.Icons.FUNCTIONS, size=46, fill=colors.FORMULA_SURFACE, color=colors.GREEN_ACCENT)], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Column([ft.Container(width=66, height=2, bgcolor=colors.GOLD), concept_node(ft.Icons.HUB, size=123, fill=colors.GOLD_SURFACE, color=colors.HOUSE_GREEN), ft.Container(width=66, height=2, bgcolor=colors.GOLD)], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Column([concept_node(ft.Icons.SPEED, size=46, fill=colors.FORMULA_SURFACE, color=colors.GREEN_ACCENT), ft.Container(width=2, height=24, bgcolor="#7da194"), concept_node(ft.Icons.LIGHTBULB_OUTLINE, size=46, fill=colors.QUESTION_SURFACE, color=colors.GOLD)], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=10), height=190, fill="#2b5148", padding=10)
        return ft.Container(ft.Column([
            ft.Row([badge("CONCEPT MATCH", fill="#2b5148", color="#d4e9e2"), text("Pair to learn", 12, color="#b7d7ca")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            visual,
            pager_title_block("Chain the concepts.", "Drag a question and its formula together."),
            ft.Row([self.pill("Start level 1", lambda _: self.start_level(1), dark=True, large=True)], alignment=ft.MainAxisAlignment.CENTER),
        ], spacing=16, expand=True), expand=True)

    def home_how_to_page(self) -> ft.Control:
        visual = hero_visual(ft.Column([
            ft.Row([illustration_card("Question", "Find the speed", fill=colors.QUESTION_SURFACE, accent=colors.GOLD, width=104, height=74), ft.Icon(ft.Icons.ARROW_FORWARD, size=27, color=colors.GOLD), illustration_card("Formula", "v = s / t", fill=colors.FORMULA_SURFACE, accent=colors.GREEN_ACCENT, width=104, height=74)], alignment=ft.MainAxisAlignment.CENTER, spacing=6),
            ft.Row([ft.Container(ft.Icon(ft.Icons.DRAG_INDICATOR, color=colors.GOLD, size=19), width=35, height=35, bgcolor="#3b665a", border_radius=18, alignment=ft.Alignment(0, 0)), ft.Container(width=67, height=2, bgcolor=colors.GOLD), ft.Container(ft.Icon(ft.Icons.AUTO_AWESOME, color=colors.FOCUS, size=19), width=35, height=35, bgcolor="#3b665a", border_radius=18, alignment=ft.Alignment(0, 0))], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
        ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER), height=180, fill="#2b5148", padding=10)
        return ft.Container(ft.Column([
            badge("HOW IT WORKS", fill="#2b5148", color="#d4e8e2"), visual,
            pager_title_block("See, drag, chain.", "All cards are visible. Drag one to its partner."),
            ft.Row([self.flow_step("01", "See", "All cards visible"), self.flow_step("02", "Drag", "Drop in workspace"), self.flow_step("03", "Chain", "Correct pairs add up")], spacing=6),
        ], spacing=14, expand=True), expand=True)

    def home_progress_page(self) -> ft.Control:
        completed = sum(1 for score in self.scores if not score.failed)
        best_combo = max((score.max_combo for score in self.scores), default=0)
        visual = hero_visual(ft.Row([progress_ring(min(1.0, completed / 2), f"{completed} / 2", size=131), ft.Column([badge("Keep building", fill=colors.GOLD_SURFACE, color=colors.HOUSE_GREEN), text("Every run counts", 14, color="#d9e8e2"), ft.Icon(ft.Icons.TRENDING_UP, size=34, color=colors.GOLD)], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER)], alignment=ft.MainAxisAlignment.CENTER, spacing=14), height=180, fill="#2b5148", padding=10)
        return ft.Container(ft.Column([
            badge("YOUR PROGRESS", fill="#2b5148", color="#d4e9e2"), visual,
            pager_title_block("Your progress", "Finish a run and your record appears here."),
            ft.Row([self.progress_metric("Completed", f"{completed} levels"), self.progress_metric("Best chain", f"×{best_combo}")], spacing=10),
        ], spacing=14, expand=True), expand=True)

    def progress_metric(self, label: str, value: str) -> ft.Container:
        return ft.Container(ft.Column([text(label, 12, color="#b7d7ca"), text(value, 21, color=colors.WHITE, weight=ft.FontWeight.W_700)], spacing=3), bgcolor="#2b5148", border_radius=14, padding=12, expand=True)

    def flow_step(self, number: str, title: str, detail: str) -> ft.Container:
        return ft.Container(ft.Column([badge(number, fill=colors.GOLD_SURFACE, color=colors.HOUSE_GREEN), text(title, 15, weight=ft.FontWeight.W_700, color=colors.HOUSE_GREEN), text(detail, 12, color=colors.INK_LIGHT, max_lines=3)], spacing=6), expand=True)

    def show_leaderboard(self):
        rows = [
            ("01", "Concept Rookie", "—"),
            ("02", "Link Master", "—"),
            ("03", "Learning Explorer", "—"),
        ]
        ranking_rows = [surface(ft.Row([
            badge(number, fill=colors.GOLD_SURFACE if number == "01" else colors.GREEN_LIGHT),
            text(name, 15, color=colors.HOUSE_GREEN, weight=ft.FontWeight.W_700),
            ft.Container(expand=True),
            text(score, 14, color=colors.INK_LIGHT),
        ], spacing=10), padding=14) for number, name, score in rows]
        content = ft.Column([
            section_title("Leaderboard", "Keep linking concepts with other learners"),
            surface(ft.Column([ft.Icon(ft.Icons.INSIGHTS_OUTLINED, color=colors.GOLD, size=36), text("Leaderboard coming soon", 20, color=colors.HOUSE_GREEN, weight=ft.FontWeight.W_700), text("Your best runs appear here once you finish a challenge.", 14, color=colors.INK_LIGHT)], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10), fill=colors.GOLD_SURFACE, padding=22),
            *ranking_rows,
        ], expand=True, spacing=14, scroll=ft.ScrollMode.AUTO)
        self.page.clean(); self.page.add(self.shell(content, show_bottom_nav=True, selected_nav=1)); self.page.update()

    def show_profile(self):
        completed = sum(1 for score in self.scores if not score.failed)
        best_combo = max((score.max_combo for score in self.scores), default=0)
        content = ft.Column([
            section_title("Profile", "Track your concept-linking journey"),
            surface(ft.Row([ft.Container(ft.Text("CM", size=18, color=colors.HOUSE_GREEN, weight=ft.FontWeight.W_700), width=58, height=58, bgcolor=colors.GOLD_SURFACE, border_radius=30, alignment=ft.Alignment(0, 0)), ft.Column([text("Concept Explorer", 20, color=colors.HOUSE_GREEN, weight=ft.FontWeight.W_700), text("Profile coming soon", 13, color=colors.INK_LIGHT)], spacing=4)], spacing=14), padding=18),
            ft.Row([stat_card("Levels cleared", f"{completed}"), stat_card("Best chain", f"×{best_combo}"), stat_card("Attempts", f"{len(self.scores)}")], spacing=8),
            surface(ft.Column([section_title("What we will track"), text("Display name, avatar, daily streak and cross-device scores will sync once the profile is live.", 14, color=colors.INK_LIGHT)], spacing=8), padding=18),
        ], expand=True, spacing=14, scroll=ft.ScrollMode.AUTO)
        self.page.clean(); self.page.add(self.shell(content, show_bottom_nav=True, selected_nav=2)); self.page.update()

    def info_tile(self, title: str, value: str) -> ft.Control:
        return stat_card(title, value)

    def show_instructions(self):
        self.page.clean()
        content = ft.Column([
            section_title("How to play", "Three steps to one match"),
            surface(ft.Column([self.flow_step("01", "Read first", "Question and formula cards are both visible. Find how they relate."), self.flow_step("02", "Then drag", "Drop the first card into the left slot, then its partner into the right slot."), self.flow_step("03", "Hold the chain", "Correct pairs grow your chain. A wrong pair locks input briefly.")], spacing=16), padding=18),
            surface(ft.Column([section_title("Pairing rules"), text("Every level is timed. More correct pairs and fewer attempts give a higher score.", 15), ft.Row([badge("Correct +1 chain", fill=colors.SUCCESS_SURFACE), badge("Wrong locks input", fill=colors.ERROR_SURFACE, color=colors.ERROR), badge("Timer zero = over", fill=colors.GOLD_SURFACE)], spacing=8, wrap=True)], spacing=12), padding=18),
            self.pill("Back to home", lambda _: self.show_home(), primary=False),
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
        self.pair_hover_card_id = None
        self.pair_slots = [None, None]
        self.pair_locked_type = None
        self.show_game()
        self.page.run_task(self.timer_loop, self.engine)

    def start_level(self, level: int):
        if not self.loading:
            self.show_loading(level)
            self.page.run_task(self.load_and_start, level)

    def show_loading(self, level: int):
        self.page.clean()
        loading = surface(ft.Column([
            ft.ProgressRing(color=colors.GREEN_ACCENT, width=34, height=34),
            text(f"Preparing level {level}", 20, color=colors.HOUSE_GREEN, weight=ft.FontWeight.W_700),
            text("Loading the latest cards…", 14, color=colors.INK_LIGHT),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10), padding=20)
        loading.width = 260
        loading.height = 150
        content = ft.Container(loading, expand=True, alignment=ft.Alignment(0, 0))
        self.page.add(self.shell(content)); self.page.update()

    async def timer_loop(self, engine: GameEngine):
        while self.engine is engine and not engine.state.is_finished:
            await asyncio.sleep(1)
            if self.engine is not engine: return
            if engine.tick():
                self.update_timer_controls(engine)
                if engine.state.is_finished:
                    await self.finish_level()

    def update_timer_controls(self, engine: GameEngine):
        """Update only the live timer widgets; rebuilding the game tree causes flicker."""
        if self.level_data is None:
            return
        duration = max(1, self.level_data.duration_seconds)
        progress = max(0.0, min(1.0, 1 - engine.state.remaining_seconds / duration))
        if self.game_timer_text is not None:
            self.game_timer_text.value = f"{engine.state.remaining_seconds}s"
        if self.game_countdown is not None:
            self.game_countdown.value = progress
            self.game_countdown.semantics_value = f"{engine.state.remaining_seconds} seconds left"
        try:
            self.page.update()
        except RuntimeError:
            pass

    async def pulse_combo(self, combo: int):
        """Pop the streak chip right after the board has been rebuilt.

        show_game() recreates the chip on every refresh, so the pop has to run
        on the fresh control: push a larger scale, let the animation declared in
        combo_badge() play, then settle back to 1.0. The pop grows with the
        streak so a long chain feels different from the first match.
        """
        chip = self.combo_badge
        if chip is None:
            return
        peak = 1.16 if combo <= 1 else 1.24 if combo == 2 else 1.32
        try:
            chip.scale = ft.Scale(peak)
            chip.update()
            await asyncio.sleep(0.12)
            chip.scale = ft.Scale(1.0)
            chip.update()
        except RuntimeError:
            # A later rebuild already replaced this control; skip the rest.
            return

    def on_card(self, card_id: str):
        if not self.engine or self.feedback_status or card_id is None:
            return
        # The pointer has left the drop target once a card is released.
        self.pair_zone_hover = False
        self.pair_hover_slot = None
        self.pair_hover_card_id = None
        card_id = str(card_id)
        candidate = self.engine.card(card_id)
        if candidate is None:
            return
        if self.card_is_pair_locked(candidate):
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
            self.page.run_task(self.pulse_combo, self.engine.state.combo)
            self.page.run_task(self.resolve_feedback)
        elif result == "selected":
            self.pair_locked_type = candidate.type
            next_slot = next((index for index, slot in enumerate(self.pair_slots) if slot is None), None)
            if next_slot is not None:
                self.pair_slots[next_slot] = candidate
            self.refresh_game()

    def pair_zone_accepts(self, event) -> bool:
        """Validate a drag before Flet treats the whole workspace as active."""
        if self._pair_zone_blocked() or all(slot is not None for slot in self.pair_slots):
            return False
        card_id = self.drag_card_id(event)
        if card_id:
            self.pair_hover_card_id = card_id
            return self._card_can_enter_pair_zone(card_id)
        # Keep the workspace visually active when Flet has accepted the drag
        # group but has not resolved the source payload yet.
        return bool(getattr(event, "accept", True))

    def pair_zone_will_accept(self, event) -> bool:
        accepted = self.pair_zone_accepts(event)
        self.pair_zone_hover = accepted
        self.pair_hover_slot = None
        self.update_pair_zone_visuals()
        # Do not rebuild the page from inside Flet's hit-test callback. A
        # rebuild here invalidates the active drag target and causes the card
        # to snap back, especially on the third row of level two.
        return accepted

    def pair_zone_accept(self, event):
        card_id = self.drag_card_id(event) or self.pair_hover_card_id
        self.pair_zone_hover = False
        self.pair_hover_slot = None
        self.pair_hover_card_id = None
        self.update_pair_zone_visuals()
        if card_id and self._card_can_enter_pair_zone(card_id):
            self.on_card(card_id)

    def pair_zone_leave(self, _event):
        self.pair_zone_hover = False
        self.pair_hover_slot = None
        self.pair_hover_card_id = None
        self.update_pair_zone_visuals()

    def _pair_zone_blocked(self) -> bool:
        return (
            not self.engine
            or bool(self.feedback_status)
            or self.engine.state.is_locked
            or self.engine.state.is_finished
            or self.engine.state.is_failed
        )

    def _card_can_enter_pair_zone(self, card_id: str) -> bool:
        if self._pair_zone_blocked() or not self.engine:
            return False
        card = self.engine.card(card_id)
        return card is not None and not card.is_matched and card_id not in self.engine.state.selected_card_ids and not self.card_is_pair_locked(card)

    def card_is_pair_locked(self, card) -> bool:
        return bool(self.pair_locked_type and card.type == self.pair_locked_type and card.id not in self.engine.state.selected_card_ids)

    def update_pair_zone_visuals(self):
        if not self.pair_zone_visuals:
            return
        for index, visual in enumerate(self.pair_zone_visuals):
            occupied = self.pair_slots[index] is not None
            is_hovered = self.pair_zone_hover
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
        if self.pair_workspace_visual is not None:
            if self.feedback_status == "success":
                self.pair_workspace_visual.bgcolor = colors.SUCCESS_SURFACE
                self.pair_workspace_visual.border = ft.Border.all(2, colors.GREEN_ACCENT)
            elif self.feedback_status == "error":
                self.pair_workspace_visual.bgcolor = colors.ERROR_SURFACE
                self.pair_workspace_visual.border = ft.Border.all(2, colors.ERROR)
            elif self.pair_zone_hover:
                self.pair_workspace_visual.bgcolor = colors.GREEN_LIGHT
                self.pair_workspace_visual.border = ft.Border.all(2, colors.GREEN_ACCENT)
            else:
                self.pair_workspace_visual.bgcolor = colors.WHITE
                self.pair_workspace_visual.border = ft.Border.all(1, colors.HAIRLINE)
            try:
                self.pair_workspace_visual.update()
            except RuntimeError:
                pass

    @staticmethod
    def drag_card_id(event) -> str | None:
        """Read drag data across Flet web/desktop event representations."""
        for candidate in (
            getattr(event, "data", None),
            getattr(getattr(event, "src", None), "data", None),
        ):
            if candidate is not None and str(candidate):
                return str(candidate)
        source_id = getattr(event, "src_id", None)
        page = getattr(event, "page", None)
        if source_id is not None and page is not None:
            source = page.get_control(source_id)
            data = getattr(source, "data", None)
            if data is not None and str(data):
                return str(data)
        return None

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
        self.pair_locked_type = None
        self.pair_zone_hover = False
        self.pair_hover_slot = None
        self.pair_hover_card_id = None
        if was_success and self.engine.state.is_finished:
            self.record_score(self.engine.state)
            self.show_level_result()
        else:
            self.refresh_game()

    def record_score(self, state):
        """Store the latest outcome for a level, upgrading failures on success."""
        score = Score(state.level, state.steps, state.remaining_seconds, state.max_combo, state.is_failed)
        existing_index = next((index for index, item in enumerate(self.scores) if item.level == state.level), None)
        if existing_index is None:
            self.scores.append(score)
        elif self.scores[existing_index].failed and not score.failed:
            self.scores[existing_index] = score

    async def finish_level(self):
        await asyncio.sleep(0.35)
        if not self.engine: return
        state = self.engine.state
        self.record_score(state)
        self.show_level_result()

    def refresh_game(self): self.show_game()

    def game_layout_width(self) -> int:
        """Return the portrait content width available inside the game shell."""
        if getattr(self, "is_web_preview", False):
            viewport_width = IPHONE_17_PRO_MAX_WIDTH
        else:
            viewport_width = getattr(self.page, "width", None) or 360
        # The shell and each white surface reserve 18px and 12px on both sides.
        return max(200, int(viewport_width) - 60)

    def show_game(self):
        if not self.engine: return
        state = self.engine.state
        duration = self.level_data.duration_seconds if self.level_data else max(1, state.remaining_seconds)
        progress = max(0.0, min(1.0, 1 - state.remaining_seconds / duration))
        selected_ids = {card.id for card in self.pair_slots if card is not None}
        feedback_ids = {card.id for card in self.feedback_cards}
        available_cards = [card for card in state.cards if card.id not in selected_ids and card.id not in feedback_ids]
        card_height = 96 if state.level == 2 else 124
        content_width = self.game_layout_width()
        card_width = max(40, min(82, (content_width - 24) // 4))
        cards = [game_card(card, selected=False, disabled=self.card_is_pair_locked(card), width=card_width, height=card_height) for card in available_cards]
        self.pair_zone_visuals = []
        self.pair_workspace_visual = None
        targets = []
        target_width = max(80, (content_width - 10) // 2)
        target_card_width = max(60, target_width - 14)
        for slot_index in range(2):
            slot_card = self.pair_slots[slot_index]
            slot_content = game_card(slot_card, selected=True, draggable=False, width=target_card_width, height=78) if slot_card else ft.Column([ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE, color=colors.INK_LIGHT, size=24), text("Drop the first card" if slot_index == 0 else "Drop the partner card", 12, color=colors.INK_LIGHT)], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5)
            target_visual = ft.Container(
                ft.Column([text(f"{slot_index + 1:02d}", 11, color=colors.INK_LIGHT, weight=ft.FontWeight.W_700), text("First card" if slot_index == 0 else "Partner", 14, color=colors.HOUSE_GREEN, weight=ft.FontWeight.W_700), slot_content], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
                bgcolor=colors.WHITE,
                border=ft.Border.all(1, colors.HAIRLINE),
                border_radius=20,
                padding=6,
                height=128,
                width=target_width,
                alignment=ft.Alignment(0, 0),
            )
            self.pair_zone_visuals.append(target_visual)
            targets.append(target_visual)
        self.update_pair_zone_visuals()
        workspace = surface(ft.Column([ft.Row([text("Pairing workspace", 16, color=colors.HOUSE_GREEN, weight=ft.FontWeight.W_700), text("Drop to snap in", 12, color=colors.INK_LIGHT)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.Row(targets, alignment=ft.MainAxisAlignment.CENTER, spacing=10)], spacing=10), padding=12)
        self.pair_workspace_visual = workspace
        target = ft.DragTarget(group="cards", on_will_accept=self.pair_zone_will_accept, on_accept=self.pair_zone_accept, on_leave=self.pair_zone_leave, content=workspace)
        # Build rows explicitly instead of relying on GridView's aspect-ratio
        # calculation. This keeps the visual cards and their hit regions from
        # extending into the pairing target below.
        card_rows = [
            ft.Row(cards[index:index + 4], alignment=ft.MainAxisAlignment.CENTER, spacing=8)
            for index in range(0, len(cards), 4)
        ]
        grid = surface(ft.Column(card_rows, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10), padding=12)
        self.combo_badge = combo_badge(state.combo)
        hud = ft.Row([ft.Column([text(f"LEVEL {state.level}", 12, color="#b7d7ca", weight=ft.FontWeight.W_700), text("Match up", 20, color=colors.WHITE, weight=ft.FontWeight.W_700)], spacing=3), ft.Row([badge(f"Steps {state.steps}", fill="#2b5148", color="#d9e8e2"), self.combo_badge], spacing=6)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        self.game_timer_text = text(f"{state.remaining_seconds}s", 13, color=colors.GOLD, weight=ft.FontWeight.W_700)
        countdown = ft.ProgressBar(value=progress, bar_height=9, color=colors.GOLD, bgcolor=colors.GREEN_UPLIFT, border_radius=8, semantics_label="Level countdown progress", semantics_value=f"{state.remaining_seconds} seconds left")
        self.game_countdown = countdown
        if self.feedback_status == "success":
            if state.combo >= 3:
                # Streak is hot: promotion from the neutral success tone to gold.
                hint_text, hint_color = f"Matched · chain ×{state.combo}! Hold it", colors.HOUSE_GREEN
            else:
                hint_text, hint_color = "Matched · keep the rhythm", colors.GREEN_LIGHT
        elif self.feedback_status == "error":
            hint_text, hint_color = "Not a match · try again shortly", "#ffd0ca"
        else:
            hint_text, hint_color = "Drag two cards into the zone below", "#D9E8E2"
        hint = ft.Text(hint_text, color=hint_color, size=14, weight=ft.FontWeight.W_600)
        explanation_view = ft.Container(
            ft.Text(f"Why: {self.feedback_explanation}", size=14, color=colors.INK, text_align=ft.TextAlign.CENTER),
            bgcolor=colors.SUCCESS_SURFACE,
            border_radius=14,
            padding=12,
            # Keep the last successful explanation visible while the next
            # pair is being considered; it is replaced/cleared on completion
            # of that next attempt.
            visible=bool(self.feedback_explanation),
        )
        if self.feedback_status == "error":
            feedback_fill = colors.ERROR_SURFACE
        elif self.feedback_status == "success":
            feedback_fill = colors.GOLD if state.combo >= 3 else colors.SUCCESS_SURFACE
        else:
            feedback_fill = colors.HOUSE_GREEN
        feedback = ft.Container(hint, bgcolor=feedback_fill, border_radius=12, padding=10)
        countdown_row = ft.Row([text("Time left", 12, color="#d9e8e2"), self.game_timer_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        content = ft.Column([ft.Container(ft.Column([hud, countdown_row, countdown, feedback], spacing=12), bgcolor=colors.HOUSE_GREEN, border_radius=22, padding=16), grid, target, explanation_view], expand=True, spacing=14, scroll=ft.ScrollMode.AUTO)
        self.page.clean(); self.page.add(self.shell(content, dark=True)); self.page.update()

    def show_level_result(self):
        if not self.engine: return
        state = self.engine.state
        completed = not state.is_failed
        result_actions = []
        if completed:
            result_actions.append(self.pill("Go to level 2" if state.level == 1 else "View results", lambda _: self.start_level(2) if state.level == 1 else self.show_summary()))
        content = ft.Column([
            ft.Container(ft.Column([badge("LEVEL COMPLETE" if completed else "TIME OUT", fill=colors.SUCCESS_SURFACE if completed else colors.ERROR_SURFACE, color=colors.HOUSE_GREEN if completed else colors.ERROR), text("Level complete" if completed else "Time up", 32, color=colors.HOUSE_GREEN if completed else colors.ERROR, weight=ft.FontWeight.W_700), text("Your concept map is getting clearer." if completed else "Try again with more time to think.", 14, color=colors.INK_MUTED)], spacing=10), bgcolor=colors.SUCCESS_SURFACE if completed else colors.ERROR_SURFACE, border_radius=22, padding=22),
            ft.Row([self.info_tile("Steps", str(state.steps)), self.info_tile("Time left", f"{state.remaining_seconds}s"), self.info_tile("Best chain", f"×{state.max_combo}")], spacing=10),
            *result_actions,
            self.pill("Back to home", lambda _: self.show_home(), primary=False),
        ], spacing=18, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO)
        self.page.clean(); self.page.add(self.shell(content)); self.page.update()

    def show_summary(self):
        rows = []
        for score in self.scores:
            left = ft.Column([
                text(f"Level {score.level}", 16, color=colors.HOUSE_GREEN, weight=ft.FontWeight.W_700),
                text("Cleared" if not score.failed else "Time up", 12, color=colors.ERROR if score.failed else colors.GREEN_ACCENT),
            ], spacing=4)
            right = ft.Column([
                text(f"{score.steps} steps", 14, weight=ft.FontWeight.W_700),
                text(f"{score.remaining_seconds}s · chain ×{score.max_combo}", 12, color=colors.INK_LIGHT),
            ], horizontal_alignment=ft.CrossAxisAlignment.END, spacing=4)
            rows.append(surface(ft.Row([left, right], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), padding=16))
        content = ft.Column([section_title("Run summary", "Your concept-link record"), surface(ft.Column([text("Rounds played", 14, color=colors.INK_LIGHT), text(f"{len(self.scores)} / 2", 28, color=colors.HOUSE_GREEN, weight=ft.FontWeight.W_700)], spacing=4), fill=colors.GOLD_SURFACE, padding=18), *rows, ft.Row([self.pill("Play again", lambda _: self.restart(), large=True)], alignment=ft.MainAxisAlignment.CENTER), ft.Row([self.pill("Back to home", lambda _: self.show_home(), primary=False, large=True)], alignment=ft.MainAxisAlignment.CENTER)], spacing=16, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO)
        self.page.clean(); self.page.add(self.shell(content)); self.page.update()

    def restart(self):
        self.scores.clear(); self.start_level(1)


def main(page: ft.Page):
    App(page)
