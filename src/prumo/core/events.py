"""Interrupções (popups, erros) — ARCHITECTURE.md §12.

Toda ação passa primeiro pelo InterruptionManager (regra de segurança
§12.1): toda interrupção presente é tratada — e CONFIRMADA fora da tela —
antes de o processamento normal continuar.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional

from prumo.core.exceptions import AutomationTimeoutError, PopupError
from prumo.core.wait import poll_until

logger = logging.getLogger("prumo")


@dataclass(frozen=True)
class Interruption:
    name: str
    detect: Callable[[], bool]
    handle: Callable[[], None]


def _saiu_da_tela(interrupcao: Interruption) -> Callable[[], bool]:
    """Condição "a interrupção não está mais na tela", amarrada a ESTA
    interrupção (uma lambda no laço capturaria a variável, não o valor)."""
    return lambda: not interrupcao.detect()


class InterruptionManager:
    """`confirm_timeout`: quanto esperar o popup sair da tela depois do
    `handle()` (a animação de fechar leva um instante). `max_rounds`: quantas
    interrupções seguidas tratar antes de concluir que alguma reaparece sem
    parar."""

    def __init__(self, *, confirm_timeout: float = 2.0, max_rounds: int = 5) -> None:
        self._interruptions: list[Interruption] = []
        self.confirm_timeout = confirm_timeout
        self.max_rounds = max_rounds

    def register(self, interruption: Interruption) -> None:
        self._interruptions.append(interruption)

    def _presente(self) -> Optional[Interruption]:
        for interruption in self._interruptions:
            if interruption.detect():
                return interruption
        return None

    def check_and_handle(self) -> Optional[Interruption]:
        """Trata TODA interrupção presente (popups empilhados: uma por rodada,
        na ordem de registro) e devolve a última tratada, ou `None`.

        Depois de cada `handle()`, CONFIRMA que ela saiu da tela — o "voltar
        ao estado anterior" do §12. Até 05/10/2026 isso não era conferido: um
        "OK" que não fechava o popup deixava a ação seguinte cair NELE, sem
        erro nenhum. Levanta `PopupError` se o popup continua lá depois de
        `confirm_timeout`, ou se mais de `max_rounds` aparecem seguidos."""
        tratada: Optional[Interruption] = None
        for _ in range(self.max_rounds):
            atual = self._presente()
            if atual is None:
                return tratada
            logger.info("interrupção detectada: %s", atual.name)
            atual.handle()
            try:
                poll_until(
                    _saiu_da_tela(atual),
                    timeout=self.confirm_timeout,
                    what=f"a interrupção '{atual.name}' sair da tela",
                    interval=0.1,
                )
            except AutomationTimeoutError as exc:
                raise PopupError(
                    f"interrupção '{atual.name}' continua presente {self.confirm_timeout}s depois de "
                    f"tratada — o handle não a fechou; nenhuma ação segue com ela na tela"
                ) from exc
            tratada = atual
        restante = self._presente()
        if restante is not None:
            raise PopupError(
                f"{self.max_rounds} interrupções tratadas seguidas e ainda há '{restante.name}' — "
                f"alguma reaparece sem parar"
            )
        return tratada
