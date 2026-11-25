import flet as ft

from app import App
from theme import colors


class FakePage:
    def __init__(self):
        self.controls = []

    def clean(self):
        self.controls.clear()

    def add(self, control):
        self.controls.append(control)

    def update(self):
        pass


def make_app() -> App:
    app = App.__new__(App)
    app.page = FakePage()
    app.is_web_preview = False
    return app


def test_shell_body_centers_content():
    app = make_app()
    shell = app.shell(ft.Text("content"))
    body = shell.controls[1]
    assert body.expand is True
    assert body.alignment == ft.Alignment(0, 0)


def test_loading_page_uses_centered_fixed_width_card():
    app = make_app()
    app.show_loading(2)
    shell = app.page.controls[0]
    body = shell.controls[1]
    content = body.content
    loading = content.content
    assert content.expand is True
    assert content.alignment == ft.Alignment(0, 0)
    assert loading.width == 260
    assert loading.height == 150
    assert any(isinstance(control, ft.ProgressRing) and control.color == colors.GREEN_ACCENT for control in loading.content.controls)
    assert any(getattr(control, "value", "") == "Preparing level 2" for control in loading.content.controls)
