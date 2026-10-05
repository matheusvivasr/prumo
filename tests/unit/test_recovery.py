import pytest

from prumo.core.exceptions import InputReleaseError, RecoveryError, UserTakeoverError
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


@pytest.mark.parametrize(
    "erro",
    [UserTakeoverError("ESC apertado"), InputReleaseError("Shift preso")],
    ids=["usuario-assumiu", "tecla-presa"],
)
def test_recover_never_retries_takeover_or_stuck_input(erro):
    # repetir um passo que clica depois que o usuário assumiu = disputar o mouse com ele
    chamadas = []
    manager = RecoveryManager(max_attempts=3)

    def passo(automator):
        chamadas.append(1)
        raise erro

    manager.register(passo)
    with pytest.raises(type(erro)) as excinfo:
        manager.recover(_FakeAutomator(GUIState.BUSY), timeout=1)

    assert excinfo.value is erro      # sobe intacta, não embrulhada em RecoveryError
    assert chamadas == [1]            # e na primeira tentativa


def test_each_lost_attempt_is_logged(caplog):
    manager = RecoveryManager(max_attempts=2)
    manager.register(lambda automator: (_ for _ in ()).throw(RuntimeError("app nao respondeu")))

    with caplog.at_level("WARNING", logger="prumo"), pytest.raises(RecoveryError):
        manager.recover(_FakeAutomator(GUIState.BUSY), timeout=1)

    falhas = [r.getMessage() for r in caplog.records if "falhou" in r.getMessage()]
    assert len(falhas) == 2 and "RuntimeError: app nao respondeu" in falhas[0]


def test_zero_attempts_is_rejected_instead_of_raising_without_a_cause():
    with pytest.raises(ValueError, match="max_attempts"):
        RecoveryManager(max_attempts=0)
