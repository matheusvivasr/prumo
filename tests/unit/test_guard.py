"""TakeoverGuard — a automação para quando o usuário assume (ARCHITECTURE.md §9.12).

Tudo via `MockDriver`: "o usuário mexeu no mouse" é atribuir `driver.cursor`;
"segurou ESC" é pôr "esc" em `driver.keys_down`.
"""

from __future__ import annotations

import pytest

from prumo.core.automator import GUIAutomator
from prumo.core.exceptions import UserTakeoverError
from prumo.core.guard import TakeoverGuard
from prumo.core.locator import PointLocator
from prumo.core.state import GUIState
from prumo.drivers.mock import MockDriver
from prumo.drivers.window import WindowGeometry


# --- a trava sozinha (como um consumidor que usa o driver direto) ---------


def test_first_check_only_looks_at_the_abort_key():
    # sem gesto anterior não há "onde deixei o mouse" — o usuário pode estar em qualquer lugar
    driver = MockDriver(cursor=(900, 900))
    TakeoverGuard(driver).check("primeiro gesto")


def test_cursor_where_the_automation_left_it_passes():
    driver = MockDriver()
    guard = TakeoverGuard(driver)
    driver.click(300, 300)
    guard.mark()
    guard.check("segundo gesto")


def test_small_drift_within_tolerance_passes():
    driver = MockDriver()
    guard = TakeoverGuard(driver, tolerance_px=8)
    driver.click(300, 300)
    guard.mark()
    driver.cursor = (305, 304)   # ~6,4 px: tremor, não mão
    guard.check()


def test_user_moving_the_mouse_between_gestures_stops_the_automation():
    driver = MockDriver()
    guard = TakeoverGuard(driver, tolerance_px=8)
    driver.click(300, 300)
    guard.mark()
    driver.cursor = (340, 300)   # 40 px: alguém pegou o mouse
    with pytest.raises(UserTakeoverError, match=r"40px.*antes de 'clicar OK'"):
        guard.check("clicar OK")


def test_holding_the_abort_key_stops_even_before_any_gesture():
    driver = MockDriver(keys_down={"esc"})
    with pytest.raises(UserTakeoverError, match="ESC"):
        TakeoverGuard(driver).check("primeiro gesto")


def test_abort_key_can_be_switched_off():
    driver = MockDriver(keys_down={"esc"})
    TakeoverGuard(driver, abort_key=None).check()


def test_forget_drops_the_reference_after_a_manual_interval():
    driver = MockDriver()
    guard = TakeoverGuard(driver)
    driver.click(300, 300)
    guard.mark()
    guard.forget()               # a automação pediu que ele fizesse algo à mão
    driver.cursor = (10, 10)
    guard.check()


# --- dentro do GUIAutomator -------------------------------------------------


class FakeWindow:
    def __init__(self):
        self.activate_calls = 0

    def find(self):
        return self

    def activate(self):
        self.activate_calls += 1

    def geometry(self):
        return WindowGeometry(left=100, top=200, width=800, height=600)

    def is_alive(self):
        return True


def make_automator(driver, *, guard=None):
    window = FakeWindow()
    automator = GUIAutomator(
        window=window,
        driver=driver,
        locators={"ok": PointLocator(x=0.5, y=0.5)},   # -> (500, 500)
        state_detector=lambda: GUIState.READY,
        guard=guard,
    )
    return automator, window


def test_without_a_guard_nothing_changes():
    driver = MockDriver(keys_down={"esc"})
    automator, _ = make_automator(driver)
    automator.click("ok")
    driver.cursor = (0, 0)
    automator.click("ok")
    assert driver.actions() == ["click", "click"]   # nem consulta o cursor nem a tecla


def test_guarded_automator_refuses_the_next_action_after_the_user_moves():
    driver = MockDriver()
    automator, _ = make_automator(driver, guard=TakeoverGuard(driver))
    automator.click("ok")
    driver.cursor = (700, 650)
    with pytest.raises(UserTakeoverError, match="250px.*press enter"):
        automator.press("enter")
    assert "press" not in driver.actions()


def test_guard_runs_before_activate_so_focus_is_not_stolen_back():
    driver = MockDriver(keys_down={"esc"})
    automator, window = make_automator(driver, guard=TakeoverGuard(driver))
    with pytest.raises(UserTakeoverError):
        automator.press("enter")
    assert window.activate_calls == 0


def test_guarded_click_at_is_checked_too():
    # click_at é chamado direto por consumidores (softkey, menu) sem passar pelo precheck
    driver = MockDriver()
    automator, _ = make_automator(driver, guard=TakeoverGuard(driver))
    automator.click_at(400, 400, rotulo="softkey F1")
    driver.cursor = (50, 50)
    with pytest.raises(UserTakeoverError, match="softkey F2"):
        automator.click_at(450, 400, rotulo="softkey F2")
    assert [c for c in driver.calls if c[0] == "click"] == [("click", (400, 400, "left", 1))]


def test_keyboard_actions_keep_the_reference_where_the_mouse_was_left():
    driver = MockDriver()
    automator, _ = make_automator(driver, guard=TakeoverGuard(driver))
    automator.click("ok")
    automator.write("abc")
    automator.hotkey("ctrl", "s")
    automator.press("enter")     # o mouse não se mexeu: tudo passa
    assert [a for a in driver.actions() if a in {"click", "write", "hotkey", "press"}] == [
        "click", "write", "hotkey", "press",
    ]
