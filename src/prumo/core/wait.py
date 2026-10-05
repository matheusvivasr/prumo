"""poll_until — esperar uma condição qualquer, com prazo (ARCHITECTURE.md §9.12).

O `StateManager.wait_until` espera um `GUIState`, e os `wait_for_template*`
do `GUIAutomator` esperam uma imagem. Faltava o caso mais simples: "chame
isto até devolver algo verdadeiro". Os dois consumidores externos escreveram
a mesma função cada um (hp-prime-CK, `_esperar`; e2e do painel-nativo da
Tina, `esperar`), que é esta.
"""

from __future__ import annotations

import time
from typing import Callable, Optional, Tuple, Type, TypeVar

from prumo.core.exceptions import AutomationTimeoutError

T = TypeVar("T")


def poll_until(
    cond: Callable[[], T],
    *,
    timeout: float,
    what: str,
    interval: float = 0.2,
    retry_on: Tuple[Type[BaseException], ...] = (),
) -> T:
    """Chama `cond()` até devolver um valor verdadeiro e devolve esse valor.

    `cond` roda ao menos uma vez, mesmo com `timeout=0`. Esgotado o prazo,
    levanta `AutomationTimeoutError` dizendo `what` — a mensagem é o
    relatório de quem lê o log depois, então diga O QUE se esperava ("o
    diálogo de salvar", não "condição").

    `retry_on`: exceções que `cond` pode levantar e que só querem dizer
    "ainda não" (ex.: o controle ainda não existe na árvore). Elas viram
    nova tentativa, e a última aparece na mensagem do timeout. Qualquer
    outra exceção sobe na hora — engolir erro por padrão seria falha calada.
    """
    fim = time.monotonic() + timeout
    ultimo: Optional[BaseException] = None
    while True:
        try:
            val = cond()
            if val:
                return val
        except retry_on as exc:  # type: ignore[misc]  - tupla vazia não captura nada
            ultimo = exc
        if time.monotonic() >= fim:
            extra = f" (último erro: {ultimo})" if ultimo is not None else ""
            raise AutomationTimeoutError(f"timeout de {timeout}s esperando {what}{extra}")
        time.sleep(interval)
