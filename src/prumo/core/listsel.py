"""ListSelector — selecionar um item de uma lista vertical POR NOME —
ARCHITECTURE.md §9.11.

Problema recorrente (hp-prime-automation, 22/09 e 29/09/2026): listas que
reordenam (catálogo por MRU) ou são maiores que a tela; um clique em posição
guardada cai no item errado. Aqui a regra é a de §9.9: **reler a lista a cada
passo**, mover UMA tecla por vez e só terminar quando o item DESTACADO é o
pedido.

Este módulo não sabe como as linhas são lidas nem como se move o destaque —
recebe as duas funções. Quem lê pode ser OCR (`prumo.drivers.ocr`), template,
cor ou acessibilidade; quem move é o `GUIAutomator.press`. Assim a lógica de
"achar, decidir o sentido, parar se ambíguo" existe uma vez só e é testável
sem GUI (basta uma lista falsa)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence

from prumo.core.exceptions import AutomationError, UnexpectedStateError
from prumo.drivers.ocr import similarity

logger = logging.getLogger("prumo")


@dataclass(frozen=True)
class Row:
    text: str
    cy: float          # posição vertical (só a ordem importa)
    selected: bool = False


class AmbiguousItemError(UnexpectedStateError):
    """Dois itens visíveis casam igualmente bem com o nome: PARA em vez de chutar."""


class ItemNotFoundError(AutomationError):
    """O item não foi achado/selecionado dentro do limite de passos."""


class ListSelector:
    def __init__(
        self,
        *,
        read_rows: Callable[[], Sequence[Row]],
        move_down: Callable[[], None],
        move_up: Callable[[], None],
        min_similarity: float = 0.85,
        ambiguity_margin: float = 0.05,
        settle_s: float = 0.3,
        max_steps: int = 60,
        on_fail: Optional[Callable[[str], None]] = None,
    ):
        self.read_rows = read_rows
        self.move_down = move_down
        self.move_up = move_up
        self.min_similarity = min_similarity
        self.ambiguity_margin = ambiguity_margin
        self.settle_s = settle_s
        self.max_steps = max_steps
        self.on_fail = on_fail

    def target(self, rows: Sequence[Row], name: str) -> Optional[Row]:
        """A linha que casa com `name` — só se for inequívoca."""
        scored = sorted(((similarity(r.text, name), r) for r in rows), key=lambda t: -t[0])
        if not scored or scored[0][0] < self.min_similarity:
            return None
        if (
            len(scored) > 1
            and scored[1][0] >= self.min_similarity
            and scored[1][0] >= scored[0][0] - self.ambiguity_margin
        ):
            raise AmbiguousItemError(
                f"'{name}' é ambíguo na lista: '{scored[0][1].text}' e '{scored[1][1].text}'"
            )
        return scored[0][1]

    def select(self, name: str) -> int:
        """Move o destaque até `name` e devolve quantas teclas gastou."""
        moves = 0
        for _ in range(self.max_steps):
            rows: List[Row] = list(self.read_rows())
            target = self.target(rows, name)
            current = next((r for r in rows if r.selected), None)
            if target is not None and current is not None and target.cy == current.cy:
                return moves
            if target is not None and current is not None:
                (self.move_down if target.cy > current.cy else self.move_up)()
            else:
                self.move_down()  # alvo fora da parte visível (ou sem destaque): rola
            moves += 1
            time.sleep(self.settle_s)
        if self.on_fail:
            self.on_fail(f"lista_sem_{name}")
        raise ItemNotFoundError(f"não achei/selecionei '{name}' em {self.max_steps} passos")
