"""TakeoverGuard — ARCHITECTURE.md §9.12.

A automação toma o mouse e o teclado de quem está na máquina. Ela não pode
ser teimosa: se a pessoa apertar a tecla de abortar, ou mexer no mouse entre
dois gestos, a automação para (`UserTakeoverError`) em vez de disputar o
cursor com ela.

Nasceu no e2e do painel-nativo da Tina (02/10/2026), que toma o mouse por
cerca de um minuto. Os outros consumidores também tomam o mouse e até então
só pediam "não mexa enquanto roda".

Uso, com o driver direto:

    guard = TakeoverGuard(driver)
    guard.check("clicar OK")   # ANTES de cada gesto
    driver.click(x, y)
    guard.mark()               # DEPOIS de cada gesto

Ou `GUIAutomator(..., guard=TakeoverGuard(driver))`, que faz as duas
chamadas em toda ação — inclusive `move_to` (hover) e `drag`. Todo gesto que
mexe no mouse precisa passar pelo automator (ou, com o driver direto, chamar
`mark()` depois): um `driver.move_to` solto entre duas ações parece, para a
trava, o usuário mexendo no mouse.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

from prumo.core.exceptions import UserTakeoverError
from prumo.drivers.base import InputDriver, KeyLatch


class TakeoverGuard:
    """`tolerance_px`: quanto o cursor pode andar sozinho entre dois gestos
    sem contar como "o usuário assumiu" (tremor da mesa, arredondamento de
    DPI). `abort_key=None` desliga a tecla de abortar e deixa só a checagem
    do mouse.

    A tecla vale SEGURADA (lida no `check()`) ou TOCADA a qualquer momento
    desde o gesto anterior — o toque fica no registrador do driver
    (`InputDriver.watch_key`; no `PyAutoGuiDriver`, um gancho de teclado, o
    mesmo do `keyboard.add_hotkey` que o `calibrate.py` do hp-prime-automation
    já usa para parar com ESC). Até 05/10/2026 só valia segurada, e o gesto
    instintivo é tocar. Um toque gera UMA parada (é consumido). Driver sem
    gancho cai no comportamento antigo: só a tecla segurada."""

    def __init__(self, driver: InputDriver, *, tolerance_px: float = 8.0, abort_key: Optional[str] = "esc"):
        self.driver = driver
        self.tolerance_px = tolerance_px
        self.abort_key = abort_key
        self._left_at: Optional[Tuple[int, int]] = None
        self._toques: Optional[KeyLatch] = driver.watch_key(abort_key) if abort_key else None

    def check(self, what: str = "") -> None:
        """Chame ANTES de cada gesto. Levanta `UserTakeoverError` se a tecla
        de abortar foi tocada desde o gesto anterior ou está apertada, ou se o
        cursor saiu de onde a automação o deixou no último `mark()`."""
        alvo = f" antes de '{what}'" if what else ""
        if self.abort_key and (self._consumir_toque() or self.driver.is_key_down(self.abort_key)):
            raise UserTakeoverError(f"{self.abort_key.upper()} apertado{alvo} — automação interrompida pelo usuário")
        if self._left_at is None:
            return
        agora = self.driver.cursor_position()
        andou = math.hypot(agora[0] - self._left_at[0], agora[1] - self._left_at[1])
        if andou > self.tolerance_px:
            raise UserTakeoverError(
                f"o mouse saiu do lugar ({andou:.0f}px) entre dois gestos{alvo} — "
                f"o usuário assumiu; automação interrompida"
            )

    def mark(self) -> None:
        """Chame DEPOIS de cada gesto: guarda onde a automação deixou o
        cursor, que é a referência do próximo `check()`."""
        self._left_at = self.driver.cursor_position()

    def forget(self) -> None:
        """Esquece a referência — e os toques de tecla registrados. Use depois
        de um intervalo em que o usuário PODE mexer no mouse e no teclado (ex.:
        a automação pediu que ele fizesse algo à mão): o que ele fez ali não é
        um "pare"."""
        self._left_at = None
        if self._toques is not None:
            self._toques.clear()

    def own_keys_sent(self, *keys: str) -> None:
        """A automação acabou de mandar `keys` pelo teclado. Se a tecla de
        abortar estava entre elas, o registrador viu o toque — e ele é NOSSO,
        não do usuário: zera, para não parar no gesto seguinte. O
        `GUIAutomator` chama isto sozinho em `press`/`hotkey`."""
        if self._toques is not None and any(_mesma_tecla(k, self.abort_key) for k in keys):
            self._toques.clear()

    def close(self) -> None:
        """Solta o gancho de teclado do registrador (vive até o fim do
        processo se ninguém chamar)."""
        if self._toques is not None:
            self._toques.close()

    def _consumir_toque(self) -> bool:
        if self._toques is not None and self._toques.fired():
            self._toques.clear()        # um toque, uma parada
            return True
        return False


_SINONIMOS = {"esc": "esc", "escape": "esc"}


def _mesma_tecla(a: str, b: Optional[str]) -> bool:
    if b is None:
        return False
    a, b = a.strip().lower(), b.strip().lower()
    return _SINONIMOS.get(a, a) == _SINONIMOS.get(b, b)
