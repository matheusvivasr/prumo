"""SoftkeyRow — ARCHITECTURE.md §9.7.

Grade de N fatias horizontais iguais, numa fileira de altura fixa (ex.:
F1-F6 de uma calculadora, ou qualquer barra de botões de largura igual no
rodapé de um app). Não é AnchorZone (§9.2) — não precisa de casamento de
imagem, é aritmética pura: a fileira fica sempre no mesmo pixel em y (chrome
do app, não escala com o conteúdo) e cada fatia tem largura igual,
proporcional à largura da janela.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Tuple

from prumo.drivers.window import WindowGeometry


@dataclass(frozen=True)
class SoftkeyRow:
    count: int
    y_offset: int
    geometry_key: Callable[[], WindowGeometry]

    def __post_init__(self) -> None:
        if isinstance(self.count, bool) or not isinstance(self.count, int) or self.count < 1:
            raise ValueError(f"count precisa ser um inteiro >= 1 (veio {self.count!r})")

    def resolve(self, index: int) -> Tuple[int, int]:
        # 2.5 passaria pela faixa e cairia na DIVISA entre duas teclas; True viraria F2
        if isinstance(index, bool) or not isinstance(index, int):
            raise ValueError(f"índice de softkey precisa ser inteiro (veio {index!r})")
        if not 0 <= index < self.count:
            raise ValueError(f"índice {index} fora do intervalo [0, {self.count})")
        geometry = self.geometry_key()
        slot_width = geometry.width / self.count
        x = geometry.left + round(slot_width * (index + 0.5))
        y = geometry.top + self.y_offset
        return x, y
