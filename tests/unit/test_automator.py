import pytest

from prumo.core.automator import GUIAutomator
from prumo.core.events import Interruption, InterruptionManager
from prumo.core.exceptions import AutomationTimeoutError, LocatorError, UnexpectedStateError
from prumo.core.locator import PointLocator, RegionLocator
from prumo.core.recovery import RecoveryManager
from prumo.core.state import GUIState
from prumo.drivers.mock import MockDriver
from prumo.drivers.window import WindowGeometry


class FakeWindow:
    """Substituto de WindowManager para testes — mesma interface pública
    (find/activate/geometry/is_alive), sem tocar em pygetwindow nem GUI."""

    def __init__(self, geometry=None, alive=True):
        self._geometry = geometry or WindowGeometry(left=100, top=200, width=800, height=600)
        self._alive = alive
        self.activate_calls = 0
        self.find_calls = 0

    def find(self):
        self.find_calls += 1
        self._alive = True
        return self

    def activate(self):
        self.activate_calls += 1

    def geometry(self):
        return self._geometry

    def is_alive(self):
        return self._alive


LOCATORS = {
    "enter_key": PointLocator(x=0.5, y=0.5),
    "display": RegionLocator(x=0.1, y=0.1, width=0.2, height=0.2),
}


def make_automator(window=None, driver=None, state_detector=None, **kwargs):
    return GUIAutomator(
        window=window or FakeWindow(),
        driver=driver or MockDriver(),
        locators=LOCATORS,
        state_detector=state_detector or (lambda: GUIState.READY),
        **kwargs,
    )


def test_click_resolves_point_locator_to_absolute_pixel():
    driver = MockDriver()
    automator = make_automator(driver=driver)

    automator.click("enter_key")

    assert driver.calls == [("click", (500, 500, "left", 1))]


def test_click_on_region_locator_uses_center():
    driver = MockDriver()
    automator = make_automator(driver=driver)

    automator.click("display")

    assert driver.calls == [("click", (260, 320, "left", 1))]


def test_click_unknown_locator_raises_locator_error():
    automator = make_automator()
    with pytest.raises(LocatorError):
        automator.click("nao_existe")


def test_precheck_finds_window_when_not_alive():
    window = FakeWindow(alive=False)
    automator = make_automator(window=window)

    automator.precheck()

    assert window.find_calls == 1
    assert window.activate_calls == 1


def test_precheck_handles_interruption_before_action():
    handled = []
    interruptions = InterruptionManager()
    interruptions.register(Interruption(name="popup", detect=lambda: True, handle=lambda: handled.append(1)))

    automator = make_automator(interruptions=interruptions)
    automator.precheck()

    assert handled == [1]


def test_ensure_ready_waits_for_state():
    states = iter([GUIState.BUSY, GUIState.READY])
    automator = make_automator(state_detector=lambda: next(states))
    assert automator.ensure_ready(timeout=1) == GUIState.READY


def test_ensure_ready_without_recovery_reraises_timeout():
    automator = make_automator(state_detector=lambda: GUIState.BUSY)
    with pytest.raises(AutomationTimeoutError):
        automator.ensure_ready(timeout=0.05)


def test_ensure_ready_uses_recovery_when_registered():
    attempts = {"n": 0}

    def flaky_state():
        attempts["n"] += 1
        return GUIState.BUSY if attempts["n"] <= 2 else GUIState.READY

    recovery = RecoveryManager(max_attempts=1)
    recovery.register(lambda automator: None)

    automator = make_automator(state_detector=flaky_state, recovery=recovery)
    assert automator.ensure_ready(timeout=0.05) == GUIState.READY


def test_transaction_commits_when_state_ends_ready():
    driver = MockDriver()
    automator = make_automator(driver=driver, state_detector=lambda: GUIState.READY)

    with automator.transaction():
        automator.click("enter_key")

    assert driver.actions() == ["click"]


def test_transaction_raises_on_unexpected_final_state():
    calls = {"n": 0}

    def detector():
        calls["n"] += 1
        return GUIState.READY if calls["n"] == 1 else GUIState.ERROR

    automator = make_automator(state_detector=detector)

    with pytest.raises(UnexpectedStateError):
        with automator.transaction():
            pass
