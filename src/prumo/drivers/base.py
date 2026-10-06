"""Contrato do driver — ARCHITECTURE.md §9.

Qualquer implementação (PyAutoGUI, um driver nativo de SO, o MockDriver de
testes) cumpre esta interface. O GUIAutomator nunca depende de detalhes de
uma implementação específica — só disto.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional, Protocol, Tuple


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
        não aparece aqui — para isso existe `watch_key`."""

    def watch_key(self, key: str) -> "KeyLatch":
        """Registrador de TOQUES de `key`: marca cada aperto no instante em
        que acontece, até ser zerado (`KeyLatch.clear`). É o que deixa a trava
        de "o usuário assumiu" pegar um toque rápido de ESC entre dois gestos
        — o gesto instintivo, que `is_key_down` perde.

        Padrão (driver que não sabe registrar toques): responde pelo estado
        do instante, como `is_key_down`. Sobrescreva quando o SO permitir um
        gancho de teclado."""
        return _LatchPorEstado(self, key)


class KeyLatch(Protocol):
    def fired(self) -> bool:
        """Houve toque desde a criação ou o último `clear()`."""
        ...

    def clear(self) -> None: ...

    def close(self) -> None:
        """Solta o gancho do SO, se houver."""
        ...


class _LatchPorEstado:
    """`KeyLatch` sem gancho: só enxerga a tecla segurada no instante."""

    def __init__(self, driver: InputDriver, key: str):
        self._driver, self._key = driver, key

    def fired(self) -> bool:
        return self._driver.is_key_down(self._key)

    def clear(self) -> None:
        pass

    def close(self) -> None:
        pass
