"""Interrupções (popups, erros) — ARCHITECTURE.md §12.

Toda ação passa primeiro pelo InterruptionManager (regra de segurança
§12.1): a primeira interrupção registrada cujo `detect()` retornar True é
tratada, e o processamento normal só continua depois disso.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger("prumo")


@dataclass(frozen=True)
class Interruption:
    name: str
    detect: Callable[[], bool]
    handle: Callable[[], None]


class InterruptionManager:
    def __init__(self) -> None:
        self._interruptions: list[Interruption] = []

    def register(self, interruption: Interruption) -> None:
        self._interruptions.append(interruption)

    def check_and_handle(self) -> Optional[Interruption]:
        for interruption in self._interruptions:
            if interruption.detect():
                logger.info("interrupção detectada: %s", interruption.name)
                interruption.handle()
                return interruption
        return None
