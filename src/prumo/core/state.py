"""Máquina de estados — ARCHITECTURE.md §10-§11.

O StateManager não sabe *como* detectar o estado — recebe um `detector`
fornecido por quem monta o GUIAutomator (cada camada conhece só o nível
imediatamente abaixo, §4). Só orquestra a espera, o polling e o timeout.
"""

from __future__ import annotations

import time
from enum import Enum, auto
from typing import Callable, Dict, Tuple

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


def color_based_detector(
    *,
    color_at: Callable[[], Tuple[int, int, int]],
    color_states: Dict[Tuple[int, int, int], GUIState],
    tolerance: int = 10,
    default: GUIState = GUIState.UNKNOWN,
) -> Callable[[], GUIState]:
    """Fábrica de `state_detector` a partir de um indicador visual — a
    forma mais comum de detecção de estado numa GUI real (§16, nota sobre
    "indicador de status" nas aplicações que já usam isso).

    `color_at` é qualquer callable sem argumento que devolve (r, g, b) —
    tipicamente `automator.color_at("nome_do_locator")` (ver
    `GUIAutomator.color_at`), passado como referência depois que o
    automator já existe. `color_states` mapeia cor esperada -> estado; a
    primeira que bater dentro da tolerância vence. Nenhuma bate -> `default`
    (UNKNOWN por padrão — estado desconhecido nunca deve ser confundido com
    READY, ver ARCHITECTURE.md §1.5).
    """

    def _matches(a: Tuple[int, int, int], b: Tuple[int, int, int]) -> bool:
        return all(abs(x - y) <= tolerance for x, y in zip(a, b))

    def detector() -> GUIState:
        cor = color_at()
        for esperada, estado in color_states.items():
            if _matches(cor, esperada):
                return estado
        return default

    return detector
