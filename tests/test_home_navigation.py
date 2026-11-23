from types import SimpleNamespace

from app import App


def make_home_app() -> App:
    app = App.__new__(App)
    app.home_page_index = 0
    app.home_pager = SimpleNamespace(selected_index=0, update=lambda: None)
    app.home_page_dots = [SimpleNamespace(width=7, bgcolor=None, update=lambda: None) for _ in range(3)]
    return app


def test_home_page_navigation_wraps_in_both_directions():
    app = make_home_app()
    app.next_home_page()
    assert app.home_page_index == 1
    app.previous_home_page()
    assert app.home_page_index == 0
    app.previous_home_page()
    assert app.home_page_index == 2
    app.next_home_page()
    assert app.home_page_index == 0


def test_home_page_navigation_updates_pager_and_indicators():
    app = make_home_app()
    app.go_to_home_page(2)
    assert app.home_pager.selected_index == 2
    assert app.home_page_dots[2].width == 22
    assert app.home_page_dots[0].width == 7


def test_home_page_change_uses_same_indicator_state():
    app = make_home_app()
    app.on_home_page_change(SimpleNamespace(control=SimpleNamespace(selected_index=1)), app.home_page_dots)
    assert app.home_page_index == 1
    assert app.home_page_dots[1].width == 22
    assert app.home_page_dots[0].width == 7


def test_home_page_change_wraps_duplicate_first_page_to_first_index():
    app = make_home_app()
    app.on_home_page_change(SimpleNamespace(control=SimpleNamespace(selected_index=3, update=lambda: None)), app.home_page_dots)

    assert app.home_page_index == 0
