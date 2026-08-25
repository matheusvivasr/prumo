import pytest

from prumo.core.exceptions import AutomationTimeoutError
from prumo.core.state import GUIState, StateManager


def test_detect_calls_detector_and_stores_last_state():
    calls = []

    def detector():
        calls.append(1)
        return GUIState.READY

    sm = StateManager(detector)
    assert sm.detect() == GUIState.READY
    assert sm.last_state == GUIState.READY
    assert len(calls) == 1


def test_wait_for_returns_immediately_when_already_in_state():
    sm = StateManager(lambda: GUIState.READY, poll_interval=0.01)
    assert sm.wait_for(GUIState.READY, timeout=1) == GUIState.READY


def test_wait_for_polls_until_state_reached():
    states = iter([GUIState.BUSY, GUIState.BUSY, GUIState.READY])
    sm = StateManager(lambda: next(states), poll_interval=0.01)
    assert sm.wait_for(GUIState.READY, timeout=1) == GUIState.READY


def test_wait_for_times_out():
    sm = StateManager(lambda: GUIState.BUSY, poll_interval=0.01)
    with pytest.raises(AutomationTimeoutError):
        sm.wait_for(GUIState.READY, timeout=0.05)


def test_wait_until_custom_condition():
    states = iter([GUIState.UNKNOWN, GUIState.ERROR, GUIState.POPUP])
    sm = StateManager(lambda: next(states), poll_interval=0.01)
    result = sm.wait_until(lambda s: s in (GUIState.ERROR, GUIState.POPUP), timeout=1)
    assert result == GUIState.ERROR
