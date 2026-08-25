"""WindowManager — ARCHITECTURE.md §8.

Responsável exclusivamente pela janela: localizar, ativar, medir,
verificar se ainda existe. A origem usada para coordenadas relativas é
(left, top) da janela, incluindo o header — mesmo critério já validado em
hp-prime-automation/core/janela_utils.py (a origem histórica do projeto).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Tuple

from prumo.core.exceptions import WindowNotFoundError

logger = logging.getLogger("prumo")


@dataclass(frozen=True)
class WindowGeometry:
    left: int
    top: int
    width: int
    height: int

    def to_absolute(self, rel_x: float, rel_y: float) -> Tuple[int, int]:
        """Converte coordenada relativa à janela (0.0-1.0) em pixel de tela."""
        return (
            self.left + round(rel_x * self.width),
            self.top + round(rel_y * self.height),
        )


class WindowManager:
    def __init__(
        self,
        title: str,
        *,
        exact: bool = False,
        attempts: int = 5,
        retry_interval: float = 0.5,
    ):
        self.title = title
        self.exact = exact
        self.attempts = attempts
        self.retry_interval = retry_interval
        self._window = None

    def find(self):
        import pygetwindow as gw

        for _ in range(self.attempts):
            candidates = [
                w
                for w in gw.getAllWindows()
                if w.title.strip()
                and (w.title == self.title if self.exact else self.title.lower() in w.title.lower())
            ]
            if candidates:
                self._window = candidates[0]
                return self._window
            time.sleep(self.retry_interval)

        raise WindowNotFoundError(
            f"nenhuma janela encontrada para título '{self.title}' "
            f"(exact={self.exact}) após {self.attempts} tentativa(s)"
        )

    def activate(self) -> None:
        window = self._window or self.find()
        try:
            if window.isMinimized:
                window.restore()
            window.activate()
        except Exception as exc:
            # algumas versões do pygetwindow levantam aviso mesmo quando funciona
            logger.debug("activate() retornou aviso (geralmente inofensivo): %s", exc)
        time.sleep(0.3)

    def geometry(self) -> WindowGeometry:
        window = self._window or self.find()
        return WindowGeometry(left=window.left, top=window.top, width=window.width, height=window.height)

    def is_alive(self) -> bool:
        if self._window is None:
            return False
        try:
            return bool(self._window.title)
        except Exception:
            return False
