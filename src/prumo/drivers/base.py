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
    def move_to(self, x: int, y: int, *, duration: float = 0.0) -> None: ...

    @abstractmethod
    def press(self, key: str) -> None: ...

    @abstractmethod
    def hotkey(self, *keys: str) -> None: ...

    @abstractmethod
    def write(self, text: str, *, delay: float = 0.0) -> None: ...

    @abstractmethod
    def drag(self, start: Tuple[int, int], end: Tuple[int, int], *, duration: float = 0.5) -> None: ...

    @abstractmethod
    def screenshot(self, region: Optional[Tuple[int, int, int, int]] = None) -> Any: ...

    @abstractmethod
    def screen_size(self) -> Tuple[int, int]: ...

    @abstractmethod
    def locate_on_screen(
        self, template_path: str, *, confidence: float = 0.85
    ) -> Optional[Tuple[float, float]]: ...

    @abstractmethod
    def read_clipboard(self) -> str: ...

    @abstractmethod
    def write_clipboard(self, text: str) -> None: ...

    # Leitura do estado de entrada do SO — base da trava de "o usuário
    # assumiu" (`core.guard.TakeoverGuard`, ARCHITECTURE.md §9.12).

    @abstractmethod
    def cursor_position(self) -> Tuple[int, int]: ...

    @abstractmethod
    def is_key_down(self, key: str) -> bool:
        """Estado da tecla NESTE instante (nome do `keyboard`: "esc",
        "shift"...). Um toque que começou e terminou entre duas consultas
        não aparece aqui."""
