from prumo.drivers.mock import MockDriver


def test_drag_registers_start_end_and_duration():
    driver = MockDriver()
    driver.drag((2, 2), (100, 200), duration=0.3)
    assert driver.calls == [("drag", ((2, 2), (100, 200), 0.3))]


def test_screen_size_returns_configured_value():
    driver = MockDriver(screen_size_return=(1280, 720))
    assert driver.screen_size() == (1280, 720)
    assert driver.actions() == ["screen_size"]


def test_actions_lists_call_names_in_order():
    driver = MockDriver()
    driver.click(1, 2)
    driver.press("a")
    driver.drag((0, 0), (1, 1))
    assert driver.actions() == ["click", "press", "drag"]


def test_locate_on_screen_returns_configured_position():
    driver = MockDriver(locate_on_screen_return={"botao.png": (50.0, 60.0)})
    assert driver.locate_on_screen("botao.png") == (50.0, 60.0)
    assert driver.calls == [("locate_on_screen", ("botao.png", 0.85))]


def test_locate_on_screen_returns_none_when_not_configured():
    driver = MockDriver()
    assert driver.locate_on_screen("ausente.png") is None
