"""Sistema de recuperação — ARCHITECTURE.md §15.

normal -> erro -> diagnóstico -> tentativa de recuperação -> verificação ->
READY. Se as tentativas se esgotarem, levanta RecoveryError encadeando a
causa original — nunca engole o erro (§1.5: falha segura).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, List, Optional

from prumo.core.exceptions import InputReleaseError, RecoveryError, UserTakeoverError
from prumo.core.state import GUIState

if TYPE_CHECKING:
    from prumo.core.automator import GUIAutomator

logger = logging.getLogger("prumo")

# Erros que a recuperação NUNCA trata como "tente de novo" — sobem na hora,
# intactos. Insistir neles piora o estado em vez de restaurá-lo:
# - o usuário assumiu o mouse/teclado: repetir um passo que clica é disputar
#   o cursor com ele (§9.12);
# - o SO não confirmou a soltura de um botão/tecla: seguir com algo preso
#   corrompe tudo o que vier depois (§9.9).
NEVER_RETRIED = (UserTakeoverError, InputReleaseError)


@dataclass
class RecoveryManager:
    steps: List[Callable[["GUIAutomator"], None]] = field(default_factory=list)
    max_attempts: int = 1

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError(f"max_attempts precisa ser >= 1 (veio {self.max_attempts})")

    def register(self, step: Callable[["GUIAutomator"], None]) -> None:
        self.steps.append(step)

    def recover(self, automator: "GUIAutomator", *, timeout: float = 5.0) -> GUIState:
        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_attempts + 1):
            logger.warning("recuperação: tentativa %s/%s", attempt, self.max_attempts)
            try:
                for step in self.steps:
                    step(automator)
                return automator.state.wait_for(GUIState.READY, timeout=timeout)
            except NEVER_RETRIED:
                raise
            except Exception as exc:  # noqa: BLE001 - qualquer outra falha conta como tentativa perdida
                logger.warning("recuperação: tentativa %s falhou: %s: %s", attempt, type(exc).__name__, exc)
                last_error = exc
                continue
        raise RecoveryError(
            f"recuperação falhou após {self.max_attempts} tentativa(s)"
        ) from last_error
