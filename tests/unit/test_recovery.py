import pytest

from prumo.core.exceptions import RecoveryError
from prumo.core.recovery import RecoveryManager
from prumo.core.state import GUIState


class _FakeAutomatorState:
    def __init__(self, state: GUIState):
        self._state = state

    def wait_for(self, state, timeout):
        if self._state != state:
            raise TimeoutError("estado nao alcancado")
        return self._state


class _FakeAutomator:
    def __init__(self, state: GUIState):
        self.state = _FakeAutomatorState(state)


def test_recover_succeeds_on_first_attempt():
    steps_ran = []
    manager = RecoveryManager()
    manager.register(lambda automator: steps_ran.append(1))

    automator = _FakeAutomator(GUIState.READY)
    result = manager.recover(automator, timeout=1)

    assert result == GUIState.READY
    assert steps_ran == [1]


def test_recover_raises_recovery_error_after_exhausting_attempts():
    manager = RecoveryManager(max_attempts=2)

    def failing_step(automator):
        raise RuntimeError("app nao respondeu")

    manager.register(failing_step)
    automator = _FakeAutomator(GUIState.BUSY)

    with pytest.raises(RecoveryError) as excinfo:
        manager.recover(automator, timeout=1)

    assert isinstance(excinfo.value.__cause__, RuntimeError)
