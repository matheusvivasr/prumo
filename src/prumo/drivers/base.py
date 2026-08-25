"""Contrato do driver — ARCHITECTURE.md §9.

Qualquer implementação (PyAutoGUI, um driver nativo de SO, o MockDriver de
testes) cumpre esta interface. O GUIAutomator nunca depende de detalhes de
uma implementação específica — só disto.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple


class InputDriver(ABC):
    @abstractmethod
    def click(self, x: int, y: int, *, button: str = "left", clicks: int = 1) -> None: ...

    @abstractmethod
    def move_to(self, x: int, y: int) -> None: ...

    @abstractmethod
    def press(self, key: str) -> None: ...

    @abstractmethod
    def hotkey(self, *keys: str) -> None: ...

    @abstractmethod
    def write(self, text: str) -> None: ...

    @abstractmethod
    def screenshot(self, region: Optional[Tuple[int, int, int, int]] = None) -> Any: ...
