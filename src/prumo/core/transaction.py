"""Transaction Manager — ARCHITECTURE.md §17.

Verifica estado inicial, executa o bloco `with`, valida estado final.
Recuperação em caso de erro é responsabilidade do RecoveryManager — esta
função só propaga a exceção, nunca a mascara.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Iterator

from prumo.core.exceptions import UnexpectedStateError
from prumo.core.state import GUIState

if TYPE_CHECKING:
    from prumo.core.automator import GUIAutomator


@contextmanager
def transaction(automator: "GUIAutomator", *, timeout: float = 5.0) -> Iterator["GUIAutomator"]:
    automator.ensure_ready(timeout=timeout)
    yield automator
    final_state = automator.state.detect()
    if final_state not in (GUIState.READY, GUIState.BUSY):
        raise UnexpectedStateError(
            f"transação terminou com estado inesperado: {final_state.name}"
        )
