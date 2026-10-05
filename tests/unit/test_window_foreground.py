"""WindowManager.owns_foreground() / ensure_foreground() — "a próxima tecla
vai pro processo certo?" (ARCHITECTURE.md §9.12).

O Win32 é stubado nas duas pontas: `_foreground_hwnd` (quem está em primeiro
plano) e `_pid` (de que processo é cada handle). O que se testa é a decisão,
não a API do Windows.
"""

from __future__ import annotations

import sys

import pytest

from prumo.core.exceptions import WindowOccludedError
from prumo.drivers.window import WindowManager

ALVO = 100        # hwnd da janela-alvo
POPUP = 101       # menu/diálogo do PRÓPRIO app: outro hwnd, mesmo processo
INTRUSA = 200     # janela de outro processo
PIDS = {ALVO: 7, POPUP: 7, INTRUSA: 9}


class FakeWindow:
    title = "Alvo"
    _hWnd = ALVO


def make_manager(monkeypatch, *, frente, pids=PIDS, activate=None):
    """`frente` é uma lista: cada consulta ao primeiro plano consome o
    próximo valor (o último se repete) — simula o `activate()` mudando quem
    está na frente entre a 1ª e a 2ª consulta."""
    monkeypatch.setattr(sys, "platform", "win32")
    fila = list(frente)
    monkeypatch.setattr(
        WindowManager, "_foreground_hwnd", staticmethod(lambda: fila.pop(0) if len(fila) > 1 else fila[0])
    )
    monkeypatch.setattr(WindowManager, "_pid", staticmethod(lambda hwnd: pids.get(int(hwnd), 0)))
    manager = WindowManager(title="Alvo")
    manager._window = FakeWindow()
    chamadas = []
    monkeypatch.setattr(manager, "activate", activate or (lambda: chamadas.append(1)))
    return manager, chamadas


def test_owns_foreground_when_the_target_itself_is_in_front(monkeypatch):
    manager, _ = make_manager(monkeypatch, frente=[ALVO])
    assert manager.owns_foreground() is True


def test_owns_foreground_when_a_popup_of_the_same_process_is_in_front(monkeypatch):
    # o caso que `isActive` erraria: o menu do próprio app é quem recebe a tecla
    manager, _ = make_manager(monkeypatch, frente=[POPUP])
    assert manager.owns_foreground() is True


def test_does_not_own_foreground_when_another_process_is_in_front(monkeypatch):
    manager, _ = make_manager(monkeypatch, frente=[INTRUSA])
    assert manager.owns_foreground() is False


def test_does_not_own_foreground_when_nothing_is_in_front(monkeypatch):
    # transição de janela, tela bloqueada: GetForegroundWindow devolve NULL
    manager, _ = make_manager(monkeypatch, frente=[0])
    assert manager.owns_foreground() is False


def test_fails_closed_when_the_target_pid_is_unknown(monkeypatch):
    # janela-alvo fechada: PID 0 nas duas pontas NÃO pode virar "mesmo processo"
    manager, _ = make_manager(monkeypatch, frente=[INTRUSA], pids={})
    assert manager.owns_foreground() is False


def test_ensure_foreground_does_nothing_when_already_owned(monkeypatch):
    manager, ativacoes = make_manager(monkeypatch, frente=[POPUP])
    manager.ensure_foreground()
    assert ativacoes == []   # não ativa: ativar fecharia o menu que ia receber a tecla


def test_ensure_foreground_activates_once_and_rechecks(monkeypatch):
    manager, ativacoes = make_manager(monkeypatch, frente=[INTRUSA, ALVO])
    manager.ensure_foreground()
    assert ativacoes == [1]


def test_ensure_foreground_raises_when_another_process_keeps_the_front(monkeypatch):
    manager, ativacoes = make_manager(monkeypatch, frente=[INTRUSA, INTRUSA])
    with pytest.raises(WindowOccludedError):
        manager.ensure_foreground()
    assert ativacoes == [1]
