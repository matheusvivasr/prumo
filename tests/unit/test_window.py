"""WindowManager.activate() — confirmação real de foreground, não só ausência
de exceção. Ver docstring de `WindowManager.activate()` (drivers/window.py)
pro achado real que motivou isso: `SetForegroundWindow` pode ser recusado
pelo Windows (foreground lock) sem levantar exceção nenhuma.

Os testes usam um `FakeWin32Window` no lugar do objeto real de
`pygetwindow` — mesma superfície que `WindowManager` usa (`isMinimized`,
`isActive`, `restore()`, `activate()`, `title`), sem depender de janela real
nem do Windows de verdade. `_soltar_tecla_alt` (o contorno de foreground
lock, que chama a API do Windows) é sempre stubado — não é o que este
arquivo testa; `WindowManager._tentar_ativar`/`isActive` é.
"""

from __future__ import annotations

import pytest

from prumo.core.exceptions import AmbiguousWindowError, WindowActivationError, WindowNotFoundError
from prumo.drivers.window import WindowManager


class FakeWin32Window:
    """`activate()` só incrementa um contador; `isActive` fica `True` a
    partir da N-ésima chamada — simula o Windows aceitando
    `SetForegroundWindow` só depois do contorno de foreground lock (ou nunca,
    se `active_after_n_activates` for maior que as tentativas totais que
    `WindowManager.activate()` faz: 2)."""

    def __init__(self, *, active_after_n_activates=1, is_minimized=False, title="HP Prime"):
        self.isMinimized = is_minimized
        self.title = title
        self._activate_calls = 0
        self._active_after_n_activates = active_after_n_activates
        self.restore_calls = 0
        self.move_calls = []

    def restore(self):
        self.restore_calls += 1
        self.isMinimized = False

    def activate(self):
        self._activate_calls += 1

    def moveTo(self, x, y):
        self.move_calls.append((x, y))

    @property
    def isActive(self):
        return self._activate_calls >= self._active_after_n_activates


def make_manager(window, monkeypatch, *, alt_tap_calls: list):
    manager = WindowManager(title=window.title)
    manager._window = window
    monkeypatch.setattr(
        WindowManager,
        "_soltar_tecla_alt",
        staticmethod(lambda: alt_tap_calls.append(1)),
    )
    return manager


def test_activate_succeeds_on_first_try_without_alt_workaround(monkeypatch):
    alt_taps = []
    window = FakeWin32Window(active_after_n_activates=1)
    manager = make_manager(window, monkeypatch, alt_tap_calls=alt_taps)

    manager.activate()

    assert window.isActive
    assert alt_taps == []  # não precisou do contorno


def test_activate_falls_back_to_alt_tap_when_first_attempt_is_refused(monkeypatch):
    """Simula o achado real: 1ª chamada de activate() não bastou (Windows
    recusou o foreground silenciosamente) — só a 2ª, depois do "soltar tecla
    Alt", deveria funcionar."""
    alt_taps = []
    window = FakeWin32Window(active_after_n_activates=2)
    manager = make_manager(window, monkeypatch, alt_tap_calls=alt_taps)

    manager.activate()

    assert window.isActive
    assert alt_taps == [1]  # contorno foi usado exatamente uma vez


def test_activate_raises_window_activation_error_if_still_not_foreground(monkeypatch):
    """Se nem o contorno resolver (outro processo retomando o foco sem
    parar), falha alto em vez de deixar quem chamou clicar às cegas numa
    janela que não está de verdade em primeiro plano."""
    alt_taps = []
    window = FakeWin32Window(active_after_n_activates=99)
    manager = make_manager(window, monkeypatch, alt_tap_calls=alt_taps)

    with pytest.raises(WindowActivationError):
        manager.activate()

    assert alt_taps == [1]  # tentou o contorno antes de desistir


def test_activate_restores_minimized_window_before_activating(monkeypatch):
    alt_taps = []
    window = FakeWin32Window(active_after_n_activates=1, is_minimized=True)
    manager = make_manager(window, monkeypatch, alt_tap_calls=alt_taps)

    manager.activate()

    assert window.restore_calls == 1
    assert not window.isMinimized


def test_move_to_calls_move_to_on_the_underlying_window():
    window = FakeWin32Window()
    manager = WindowManager(title=window.title)
    manager._window = window

    manager.move_to(0, 0)

    assert window.move_calls == [(0, 0)]


def test_move_to_finds_window_first_if_not_already_found(monkeypatch):
    window = FakeWin32Window()
    manager = WindowManager(title=window.title)
    monkeypatch.setattr(WindowManager, "find", lambda self: window)

    manager.move_to(10, 20)

    assert window.move_calls == [(10, 20)]


def test_find_with_multiple_matching_candidates_picks_by_list_order_not_by_correctness(monkeypatch):
    """Achado real (22/09/2026, sessão hp-prime-automation — ver
    prumo/ARCHITECTURE.md §9.8 pro achado irmão sobre Shift+tecla): busca por
    substring (`exact=False`, o padrão) casa com QUALQUER janela cujo título
    contenha o termo — inclusive instâncias duplicadas que o Windows sufixa
    sozinho quando o mesmo executável é aberto de novo (`HP Prime_2`,
    `HP Prime_3`...). `find()` devolve `candidates[0]`: a ORDEM que
    `getAllWindows()` lista as janelas decide qual a automação usa, não
    qual delas tem o estado/config esperado. Isso já causou confusão real:
    abrir a Virtual Calculator via `open_application` (fora do
    `run_macro.py`) quando uma instância já estava rodando criou 3 janelas
    extras (`HP Prime_1/_2/_3`), e `find()` não tem como saber que só a
    original importa.

    Até 05/10/2026 este teste TRAVAVA esse comportamento ("pega a primeira
    da lista"), com a leitura de que a causa raiz era deixar instâncias
    abertas. No hardening (v0.9) virou o contrário: a ordem do SO não pode
    decidir onde a automação age. O título exatamente igual desempata — é a
    instância original, a que o achado dizia ser a única que importa."""
    janela_duplicada = FakeWin32Window(title="HP Prime_2")
    janela_original = FakeWin32Window(title="HP Prime")
    monkeypatch.setattr(
        "pygetwindow.getAllWindows",
        lambda: [janela_duplicada, janela_original],  # ordem arbitrária do SO
    )
    manager = WindowManager(title="HP Prime")  # exact=False (padrão)

    achada = manager.find()

    assert achada is janela_original  # a de título exato, não a primeira da lista


def test_find_refuses_to_guess_when_nothing_breaks_the_tie(monkeypatch):
    # duas instâncias com o MESMO título (ex.: o painel real aberto + o de teste)
    a, b = FakeWin32Window(title="Tina — Supervisório"), FakeWin32Window(title="Tina — Supervisório")
    monkeypatch.setattr("pygetwindow.getAllWindows", lambda: [a, b])

    with pytest.raises(AmbiguousWindowError, match="2 janelas.*pid="):
        WindowManager(title="Tina — Supervisório", exact=True).find()


def test_find_refuses_substring_matches_without_an_exact_one(monkeypatch):
    a, b = FakeWin32Window(title="HP Prime_2"), FakeWin32Window(title="HP Prime_3")
    monkeypatch.setattr("pygetwindow.getAllWindows", lambda: [a, b])

    with pytest.raises(AmbiguousWindowError, match="'HP Prime_2', 'HP Prime_3'"):
        WindowManager(title="HP Prime").find()


def test_ambiguity_is_not_a_not_found_error():
    # quem trata "não achei" abrindo o app abriria MAIS uma instância
    assert not issubclass(AmbiguousWindowError, WindowNotFoundError)


def test_pid_picks_the_instance_you_opened(monkeypatch):
    real, teste = FakeWin32Window(title="Painel"), FakeWin32Window(title="Painel")
    real._hWnd, teste._hWnd = 1, 2
    monkeypatch.setattr("pygetwindow.getAllWindows", lambda: [real, teste])
    monkeypatch.setattr(WindowManager, "_pid", staticmethod(lambda hwnd: {1: 500, 2: 600}[int(hwnd)]))

    assert WindowManager(title="Painel", exact=True, pid=600).find() is teste


def test_pid_without_a_matching_window_is_not_found(monkeypatch):
    real = FakeWin32Window(title="Painel")
    real._hWnd = 1
    monkeypatch.setattr("pygetwindow.getAllWindows", lambda: [real])
    monkeypatch.setattr(WindowManager, "_pid", staticmethod(lambda hwnd: 500))

    with pytest.raises(WindowNotFoundError, match="pid=600"):
        WindowManager(title="Painel", exact=True, pid=600, attempts=1, retry_interval=0).find()
