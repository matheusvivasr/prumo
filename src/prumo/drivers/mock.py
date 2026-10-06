"""MockDriver — ARCHITECTURE.md §9.1.

Registra a sequência de ações em vez de executá-las de verdade. Permite
testar core/ e drivers/ sem abrir nenhuma aplicação real — a Etapa 7 do
ROADMAP.md exige isso antes de crescer a API de qualquer aplicação.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from prumo.drivers.base import InputDriver


@dataclass
class MockDriver(InputDriver):
    """`cursor` acompanha os gestos (clique, movimento e fim do arrasto o
    levam junto, como no SO); um teste simula "o usuário mexeu no mouse"
    atribuindo `cursor` direto, "segurou ESC" pondo a tecla em `keys_down`,
    e "tocou ESC" (apertou e soltou entre duas consultas) com `tap("esc")`."""

    calls: List[Tuple[str, Any]] = field(default_factory=list)
    screenshot_return: Any = None
    screen_size_return: Tuple[int, int] = (1920, 1080)
    locate_on_screen_return: Dict[str, Optional[Tuple[float, float]]] = field(default_factory=dict)
    read_clipboard_return: str = ""
    cursor: Tuple[int, int] = (0, 0)
    keys_down: Set[str] = field(default_factory=set)
    # consultas de estado de entrada (as da trava, §9.12) ficam FORA de `calls`:
    # são bookkeeping, não ações — ligar a trava não muda a sequência de ações
    probes: List[Tuple[str, Any]] = field(default_factory=list)
    _latches: List["MockLatch"] = field(default_factory=list, repr=False)

    def watch_key(self, key: str) -> "MockLatch":
        self.probes.append(("watch_key", key))
        latch = MockLatch(key)
        self._latches.append(latch)
        return latch

    def tap(self, key: str) -> None:
        """Simula um toque do usuário: aperta e solta entre duas consultas —
        `is_key_down` não vê nada, só os registradores de `watch_key`."""
        for latch in self._latches:
            if latch.key == key and not latch.closed:
                latch._disparou = True

    def click(self, x: int, y: int, *, button: str = "left", clicks: int = 1) -> None:
        self.calls.append(("click", (x, y, button, clicks)))
        self.cursor = (x, y)

    def move_to(self, x: int, y: int, *, duration: float = 0.0) -> None:
        self.calls.append(("move_to", (x, y, duration)))
        self.cursor = (x, y)

    def press(self, key: str) -> None:
        self.calls.append(("press", key))
        self.tap(key)            # como o gancho real: ele também vê a tecla que a automação injeta

    def hotkey(self, *keys: str) -> None:
        self.calls.append(("hotkey", keys))
        for k in keys:
            self.tap(k)

    def write(self, text: str, *, delay: float = 0.0) -> None:
        self.calls.append(("write", (text, delay)))

    def drag(self, start: Tuple[int, int], end: Tuple[int, int], *, duration: float = 0.5) -> None:
        self.calls.append(("drag", (start, end, duration)))
        self.cursor = (end[0], end[1])

    def screenshot(self, region: Optional[Tuple[int, int, int, int]] = None):
        self.calls.append(("screenshot", region))
        return self.screenshot_return

    def screen_size(self) -> Tuple[int, int]:
        self.calls.append(("screen_size", None))
        return self.screen_size_return

    def locate_on_screen(
        self, template_path: str, *, confidence: float = 0.85
    ) -> Optional[Tuple[float, float]]:
        self.calls.append(("locate_on_screen", (template_path, confidence)))
        return self.locate_on_screen_return.get(template_path)

    def read_clipboard(self) -> str:
        self.calls.append(("read_clipboard", None))
        return self.read_clipboard_return

    def write_clipboard(self, text: str) -> None:
        self.calls.append(("write_clipboard", text))

    def cursor_position(self) -> Tuple[int, int]:
        self.probes.append(("cursor_position", None))
        return self.cursor

    def is_key_down(self, key: str) -> bool:
        self.probes.append(("is_key_down", key))
        return key in self.keys_down

    def actions(self) -> List[str]:
        """Nomes das ações registradas, na ordem — útil em asserts de teste."""
        return [name for name, _ in self.calls]


@dataclass
class MockLatch:
    """`KeyLatch` do `MockDriver`: dispara com `MockDriver.tap(key)`."""

    key: str
    _disparou: bool = False
    closed: bool = False

    def fired(self) -> bool:
        return self._disparou

    def clear(self) -> None:
        self._disparou = False

    def close(self) -> None:
        self.closed = True
