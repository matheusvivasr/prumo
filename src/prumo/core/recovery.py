"""Sistema de recuperação — ARCHITECTURE.md §15.

normal -> erro -> diagnóstico -> tentativa de recuperação -> verificação ->
READY. Se as tentativas se esgotarem, levanta RecoveryError encadeando a
causa original — nunca engole o erro (§1.5: falha segura).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, List, Optional

from prumo.core.exceptions import RecoveryError
from prumo.core.state import GUIState

if TYPE_CHECKING:
    from prumo.core.automator import GUIAutomator

logger = logging.getLogger("prumo")


@dataclass
class RecoveryManager:
    steps: List[Callable[["GUIAutomator"], None]] = field(default_factory=list)
    max_attempts: int = 1

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
            except Exception as exc:
                last_error = exc
                continue
        raise RecoveryError(
            f"recuperação falhou após {self.max_attempts} tentativa(s)"
        ) from last_error
