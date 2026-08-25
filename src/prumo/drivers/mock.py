"""MockDriver — ARCHITECTURE.md §9.1.

Registra a sequência de ações em vez de executá-las de verdade. Permite
testar core/ e drivers/ sem abrir nenhuma aplicação real — a Etapa 7 do
ROADMAP.md exige isso antes de crescer a API de qualquer aplicação.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

from prumo.drivers.base import InputDriver


@dataclass
class MockDriver(InputDriver):
    calls: List[Tuple[str, Any]] = field(default_factory=list)
    screenshot_return: Any = None

    def click(self, x: int, y: int, *, button: str = "left", clicks: int = 1) -> None:
        self.calls.append(("click", (x, y, button, clicks)))

    def move_to(self, x: int, y: int) -> None:
        self.calls.append(("move_to", (x, y)))

    def press(self, key: str) -> None:
        self.calls.append(("press", key))

    def hotkey(self, *keys: str) -> None:
        self.calls.append(("hotkey", keys))

    def write(self, text: str) -> None:
        self.calls.append(("write", text))

    def screenshot(self, region: Optional[Tuple[int, int, int, int]] = None):
        self.calls.append(("screenshot", region))
        return self.screenshot_return

    def actions(self) -> List[str]:
        """Nomes das ações registradas, na ordem — útil em asserts de teste."""
        return [name for name, _ in self.calls]
