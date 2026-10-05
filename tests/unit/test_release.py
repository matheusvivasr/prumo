"""Soltura confirmada como função pública (drivers/release.py, ARCHITECTURE.md §9.12).

A consulta ao SO é trocada por `is_down`: um dicionário de "quantas
consultas até soltar" por entrada.
"""

from __future__ import annotations

import pytest

from prumo.core.exceptions import InputReleaseError
from prumo.drivers.release import DEFAULT_INPUTS, confirm_released, held_inputs


def solta_depois_de(**consultas):
    """`is_down` em que cada entrada fica apertada pelas N primeiras consultas
    a ela (`-1` = nunca solta)."""
    restante = dict(consultas)

    def is_down(name):
        n = restante.get(name, 0)
        if n == 0:
            return False
        if n > 0:
            restante[name] = n - 1
        return True

    return is_down


def test_nothing_held_returns_immediately():
    confirm_released(is_down=lambda name: False)


def test_default_set_is_both_buttons_and_the_modifiers():
    assert set(DEFAULT_INPUTS) == {"mouse_left", "mouse_right", "shift", "ctrl", "alt"}


def test_held_inputs_lists_what_is_down_now():
    is_down = lambda name: name in {"shift", "mouse_left"}
    assert held_inputs(is_down=is_down) == ["mouse_left", "shift"]


def test_waits_until_the_os_reports_the_release():
    confirm_released(timeout=1, interval=0.001, is_down=solta_depois_de(ctrl=3))


def test_raises_naming_what_stayed_down():
    with pytest.raises(InputReleaseError, match="soltura de: alt"):
        confirm_released(timeout=0.02, interval=0.005, is_down=solta_depois_de(alt=-1))


def test_only_the_requested_inputs_are_checked():
    # o clique esquerdo terminou; o Shift que o USUÁRIO segura não é assunto deste gesto
    confirm_released(("mouse_left",), timeout=0.02, is_down=lambda name: name == "shift")


def test_unknown_input_name_is_a_programming_error_not_a_silent_pass():
    with pytest.raises(ValueError, match="desconhecida"):
        held_inputs(("mouse_lft",), is_down=lambda name: False)
