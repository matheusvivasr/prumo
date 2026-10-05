"""Soltura confirmada no SO, para qualquer caminho de entrada (ARCHITECTURE.md §9.9, §9.12).

O `PyAutoGuiDriver` já confirma a soltura depois de cada gesto. Mas quem
manda entrada por outro caminho (UI Automation, `SendKeys`, `pywinauto`)
também precisa da regra: seguir com botão ou modificador apertado corrompe o
que vem depois — e, num emulador, deixa tecla presa até reiniciá-lo. O
hp-prime-CK reimplementou isto em ctypes (29/09/2026) por não ter de onde
importar.
"""

from __future__ import annotations

import time
from typing import Callable, Iterable, List, Optional

from prumo.core.exceptions import InputReleaseError
from prumo.drivers._plataforma import sem_win32

# códigos de tecla virtual do Windows (GetAsyncKeyState)
VIRTUAL_KEYS = {
    "mouse_left": 0x01,
    "mouse_right": 0x02,
    "mouse_middle": 0x04,
    "shift": 0x10,
    "ctrl": 0x11,
    "alt": 0x12,
}

# o que, apertado, contamina a próxima ação: os dois botões e os modificadores
DEFAULT_INPUTS = ("mouse_left", "mouse_right", "shift", "ctrl", "alt")


def _is_down_win32(name: str) -> bool:
    if sem_win32("confirmação de soltura (drivers.release)"):
        return False  # sem como checar — e o aviso já foi pro log
    import ctypes

    return bool(ctypes.windll.user32.GetAsyncKeyState(VIRTUAL_KEYS[name]) & 0x8000)


def held_inputs(
    names: Iterable[str] = DEFAULT_INPUTS, *, is_down: Optional[Callable[[str], bool]] = None
) -> List[str]:
    """Quais de `names` estão apertados AGORA, segundo o SO."""
    consulta = is_down or _is_down_win32
    nomes = list(names)
    desconhecidos = [n for n in nomes if n not in VIRTUAL_KEYS]
    if desconhecidos:
        raise ValueError(f"entrada(s) desconhecida(s): {desconhecidos}; conhecidas: {sorted(VIRTUAL_KEYS)}")
    return [n for n in nomes if consulta(n)]


def confirm_released(
    names: Iterable[str] = DEFAULT_INPUTS,
    *,
    timeout: float = 1.0,
    interval: float = 0.02,
    is_down: Optional[Callable[[str], bool]] = None,
) -> None:
    """Só devolve quando o SO diz que tudo em `names` está solto. Levanta
    `InputReleaseError` com o nome do que continuou apertado depois de
    `timeout`. `is_down` substitui a consulta ao SO (testes)."""
    nomes = list(names)
    prazo = time.monotonic() + timeout
    while True:
        presas = held_inputs(nomes, is_down=is_down)
        if not presas:
            return
        if time.monotonic() > prazo:
            raise InputReleaseError(f"o SO não confirmou a soltura de: {', '.join(presas)}")
        time.sleep(interval)
