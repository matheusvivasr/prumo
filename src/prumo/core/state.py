"""Máquina de estados — ARCHITECTURE.md §10-§11.

O StateManager não sabe *como* detectar o estado — recebe um `detector`
fornecido por quem monta o GUIAutomator (cada camada conhece só o nível
imediatamente abaixo, §4). Só orquestra a espera, o polling e o timeout.
"""

from __future__ import annotations

import time
from enum import Enum, auto
from typing import Callable

from prumo.core.exceptions import AutomationTimeoutError


class GUIState(Enum):
    UNKNOWN = auto()
    READY = auto()
    BUSY = auto()
    ERROR = auto()
    POPUP = auto()
    CLOSED = auto()


class StateManager:
    def __init__(self, detector: Callable[[], GUIState], *, poll_interval: float = 0.2):
        self._detector = detector
        self.poll_interval = poll_interval
        self._last_state = GUIState.UNKNOWN

    @property
    def last_state(self) -> GUIState:
        return self._last_state

    def detect(self) -> GUIState:
        self._last_state = self._detector()
        return self._last_state

    def wait_for(self, state: GUIState, timeout: float) -> GUIState:
        return self.wait_until(lambda current: current == state, timeout=timeout)

    def wait_until(self, condition: Callable[[GUIState], bool], timeout: float) -> GUIState:
        deadline = time.monotonic() + timeout
        current = self.detect()
        while not condition(current):
            if time.monotonic() >= deadline:
                raise AutomationTimeoutError(
                    f"timeout de {timeout}s esperando condição de estado; último estado: {current.name}"
                )
            time.sleep(self.poll_interval)
            current = self.detect()
        return current
