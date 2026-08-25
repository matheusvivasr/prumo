import pytest

from prumo.core.exceptions import AutomationTimeoutError
from prumo.core.state import GUIState, StateManager, color_based_detector


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


COLOR_STATES = {(0, 255, 0): GUIState.READY, (255, 0, 0): GUIState.ERROR}


def test_color_based_detector_matches_exact_color():
    detector = color_based_detector(color_at=lambda: (0, 255, 0), color_states=COLOR_STATES)
    assert detector() == GUIState.READY


def test_color_based_detector_matches_within_tolerance():
    detector = color_based_detector(
        color_at=lambda: (5, 250, 3), color_states=COLOR_STATES, tolerance=10
    )
    assert detector() == GUIState.READY


def test_color_based_detector_falls_back_to_default_when_no_color_matches():
    detector = color_based_detector(color_at=lambda: (128, 128, 128), color_states=COLOR_STATES)
    assert detector() == GUIState.UNKNOWN  # default


def test_color_based_detector_custom_default():
    detector = color_based_detector(
        color_at=lambda: (1, 1, 1), color_states=COLOR_STATES, default=GUIState.POPUP
    )
    assert detector() == GUIState.POPUP


def test_color_based_detector_first_match_wins_on_ambiguous_colors():
    """Se duas cores no dict caem dentro da tolerância da mesma leitura, a
    primeira que bater vence — dict do Python preserva ordem de inserção."""
    estados = {(0, 0, 0): GUIState.ERROR, (5, 5, 5): GUIState.READY}
    detector = color_based_detector(color_at=lambda: (3, 3, 3), color_states=estados, tolerance=10)
    assert detector() == GUIState.ERROR


def test_color_based_detector_plugs_into_state_manager():
    """Uso real: o detector vira o callable que StateManager espera."""
    leituras = iter([(128, 128, 128), (0, 255, 0)])
    detector = color_based_detector(color_at=lambda: next(leituras), color_states=COLOR_STATES)
    sm = StateManager(detector, poll_interval=0.01)

    assert sm.wait_for(GUIState.READY, timeout=1) == GUIState.READY
