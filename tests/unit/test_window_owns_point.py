"""WindowManager.owns_point() — "de quem é este pixel?" (ARCHITECTURE.md §9.9).

O gate principal do `prumo` só era testado por fora (o `GUIAutomator` com uma
janela falsa). Aqui a decisão é testada por dentro: as três consultas ao Win32
(`WindowFromPoint`, `GetAncestor`, PID do handle) são stubadas, e o que se
confere é o veredito.
"""

from __future__ import annotations

import logging
import sys

from prumo.drivers import _plataforma
from prumo.drivers.window import WindowManager

ALVO = 100           # a janela-alvo (raiz)
FILHO = 101          # um controle dentro dela
POPUP = 102          # menu do PRÓPRIO app: outra raiz, mesmo processo
INTRUSA = 200        # janela de outro processo por cima
RAIZ = {ALVO: ALVO, FILHO: ALVO, POPUP: POPUP, INTRUSA: INTRUSA}
PIDS = {ALVO: 7, POPUP: 7, INTRUSA: 9}


class FakeWindow:
    title = "Alvo"

    def __init__(self, hwnd=ALVO):
        self._hWnd = hwnd


def make_manager(monkeypatch, *, no_ponto, pids=PIDS, window=None):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(WindowManager, "_window_from_point", staticmethod(lambda x, y: no_ponto))
    monkeypatch.setattr(WindowManager, "_root_ancestor", staticmethod(lambda hwnd: RAIZ.get(hwnd, 0)))
    monkeypatch.setattr(WindowManager, "_pid", staticmethod(lambda hwnd: pids.get(int(hwnd), 0)))
    manager = WindowManager(title="Alvo")
    manager._window = window or FakeWindow()
    return manager


def test_a_child_control_of_the_target_is_owned(monkeypatch):
    assert make_manager(monkeypatch, no_ponto=FILHO).owns_point(10, 10) is True


def test_a_popup_of_the_same_process_is_owned(monkeypatch):
    # achado real: o menu "Editar" da HP Prime foi barrado como oclusão na 1ª versão
    assert make_manager(monkeypatch, no_ponto=POPUP).owns_point(10, 10) is True


def test_a_window_of_another_process_on_top_is_not_owned(monkeypatch):
    # achado real (22/09/2026): o app do Claude por cima da HP Prime ativa
    assert make_manager(monkeypatch, no_ponto=INTRUSA).owns_point(10, 10) is False


def test_no_window_at_the_point_is_not_owned(monkeypatch):
    assert make_manager(monkeypatch, no_ponto=0).owns_point(10, 10) is False


def test_dead_target_never_matches_by_two_zero_pids(monkeypatch):
    # janela-alvo destruída: PID 0; um ponto de raiz desconhecida também dá 0
    assert make_manager(monkeypatch, no_ponto=INTRUSA, pids={}).owns_point(10, 10) is False


def test_a_window_without_a_win32_handle_passes_but_says_so_once(monkeypatch, caplog):
    # o pygetwindow real sempre expõe _hWnd; dublês de teste dos consumidores
    # (hp-prime-automation) não. Antes deixava passar EM SILÊNCIO; levantar
    # quebrava 9 testes do consumidor sem proteger nada em produção.
    monkeypatch.setattr(_plataforma, "_avisados", set())
    manager = make_manager(monkeypatch, no_ponto=INTRUSA, window=FakeWindow(hwnd=None))

    with caplog.at_level(logging.WARNING, logger="prumo"):
        assert manager.owns_point(10, 10) is True
        assert manager.owns_foreground() is True

    avisos = [r.getMessage() for r in caplog.records if "_hWnd" in r.getMessage()]
    assert len(avisos) == 1 and "DESLIGADOS" in avisos[0]


def test_off_windows_the_gates_pass_but_say_so_once(monkeypatch, caplog):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(_plataforma, "_avisados", set())
    manager = WindowManager(title="Alvo")
    manager._window = FakeWindow()

    with caplog.at_level(logging.WARNING, logger="prumo"):
        assert manager.owns_point(1, 1) is True
        assert manager.owns_point(2, 2) is True
        assert manager.owns_foreground() is True

    avisos = [r.getMessage() for r in caplog.records if "DESLIGADA" in r.getMessage()]
    assert len(avisos) == 2      # um por proteção, não um por chamada
    assert any("owns_point" in a for a in avisos) and any("owns_foreground" in a for a in avisos)
