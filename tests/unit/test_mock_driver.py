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


def test_read_clipboard_returns_configured_value():
    driver = MockDriver(read_clipboard_return="42")
    assert driver.read_clipboard() == "42"
    assert driver.calls == [("read_clipboard", None)]


def test_write_clipboard_registers_text():
    driver = MockDriver()
    driver.write_clipboard("PROGRAM_TEXT")
    assert driver.calls == [("write_clipboard", "PROGRAM_TEXT")]


def test_move_to_registers_duration_default_zero():
    driver = MockDriver()
    driver.move_to(10, 20)
    assert driver.calls == [("move_to", (10, 20, 0.0))]


def test_move_to_registers_explicit_duration():
    driver = MockDriver()
    driver.move_to(10, 20, duration=0.2)
    assert driver.calls == [("move_to", (10, 20, 0.2))]


def test_write_registers_delay_default_zero():
    driver = MockDriver()
    driver.write("ola")
    assert driver.calls == [("write", ("ola", 0.0))]


def test_write_registers_explicit_delay():
    driver = MockDriver()
    driver.write("ola", delay=0.08)
    assert driver.calls == [("write", ("ola", 0.08))]
