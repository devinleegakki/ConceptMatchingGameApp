"""Flet packaging entry point."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import flet as ft
from app import main


IPHONE_18_PRO_MAX_WIDTH = 440
IPHONE_18_PRO_MAX_HEIGHT = 956


def run_app(page: ft.Page) -> None:
    """Start the desktop preview on a fixed iPhone-sized portrait canvas."""
    if not getattr(page, "web", False):
        window = getattr(page, "window", None)
        if window is not None:
            window.width = IPHONE_18_PRO_MAX_WIDTH
            window.height = IPHONE_18_PRO_MAX_HEIGHT
            window.min_width = IPHONE_18_PRO_MAX_WIDTH
            window.max_width = IPHONE_18_PRO_MAX_WIDTH
            window.min_height = IPHONE_18_PRO_MAX_HEIGHT
            window.max_height = IPHONE_18_PRO_MAX_HEIGHT
            window.resizable = False
            window.center()
    main(page)


if __name__ == "__main__":
    ft.run(run_app)

