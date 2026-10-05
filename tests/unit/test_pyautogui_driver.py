"""PyAutoGuiDriver — o código que de fato mexe no mouse e no teclado.

Até 05/10/2026 tinha 0% de cobertura. Aqui `pyautogui`, `keyboard`, o relógio
e a confirmação de soltura são dublês que GRAVAM cada gesto, então dá para
afirmar a ordem dos eventos e, sobretudo, simular interrupção (Ctrl+C no meio
do "segurar", FAILSAFE no canto, `dragTo` interrompido) e provar que nada
fica preso no SO (ARCHITECTURE.md §9.9).
"""

from __future__ import annotations

import ctypes
import logging
import sys

import pytest

from prumo.core.exceptions import InputReleaseError, LocatorError
from prumo.drivers import pyautogui_driver as modulo
from prumo.drivers.pacing import HumanPacing
from prumo.drivers.pyautogui_driver import PyAutoGuiDriver

RAPIDO = HumanPacing(jitter=0, release_timeout_s=0.02)


class FailSafe(Exception):
    pass


class FakePyAutoGui:
    ImageNotFoundException = type("ImageNotFoundException", (Exception,), {})

    def __init__(self):
        self.FAILSAFE = None
        self.PAUSE = None
        self.calls = []
        self.pos = (0, 0)
        self.apertado = False
        self.mouseup_falha = None      # exceção a levantar no próximo mouseUp com coordenadas
        self.drag_falha = None
        self.achado = None             # caixa devolvida pelo locateOnScreen
        self.agulha = None             # o que o locateOnScreen recebeu

    @staticmethod
    def easeInOutQuad(t):
        return t

    def position(self):
        return self.pos

    def moveTo(self, x, y, duration=0.0, tween=None):
        self.calls.append(("moveTo", x, y))
        self.pos = (x, y)

    def mouseDown(self, x=None, y=None, button="left"):
        self.calls.append(("down", button))
        self.apertado = True

    def mouseUp(self, x=None, y=None, button="left"):
        if x is not None and self.mouseup_falha is not None:
            erro, self.mouseup_falha = self.mouseup_falha, None
            raise erro
        self.calls.append(("up", button, "com-coord" if x is not None else "sem-mover", self.FAILSAFE))
        self.apertado = False

    def click(self, x, y, button="left", clicks=1):
        self.calls.append(("click-cru", x, y, button, clicks))

    def dragTo(self, x, y, duration=0.0, button="left"):
        self.apertado = True
        if self.drag_falha is not None:
            raise self.drag_falha            # sai com o botão apertado, como o pyautogui real
        self.calls.append(("dragTo", x, y))
        self.apertado = False
        self.pos = (x, y)

    def screenshot(self, region=None):
        return ("tela", region)

    def size(self):
        return (1366, 768)

    def locateOnScreen(self, needle, confidence=0.9):
        self.agulha = needle
        if self.achado is None:
            raise self.ImageNotFoundException()
        return self.achado

    def center(self, box):
        left, top, w, h = box
        return (left + w // 2, top + h // 2)


class FakeKeyboard:
    def __init__(self):
        self.calls = []
        self.presas = set()
        self.nunca_solta = set()

    def press(self, k):
        self.calls.append(("press", k))
        self.presas.add(k)

    def release(self, k):
        self.calls.append(("release", k))
        if k not in self.nunca_solta:
            self.presas.discard(k)

    def is_pressed(self, k):
        return k in self.presas

    def send(self, s):
        self.calls.append(("send", s))

    def write(self, s):
        self.calls.append(("write", s))


@pytest.fixture
def ambiente(monkeypatch):
    """Monta o driver com dublês. `ambiente.interromper_no_segurar = True`
    faz o primeiro sleep depois de um mouseDown/press levantar Ctrl+C."""
    pg, kb = FakePyAutoGui(), FakeKeyboard()
    monkeypatch.setitem(sys.modules, "pyautogui", pg)
    monkeypatch.setitem(sys.modules, "keyboard", kb)
    monkeypatch.setattr(PyAutoGuiDriver, "_ensure_dpi_awareness", staticmethod(lambda: None))

    class Estado:
        interromper_no_segurar = False
        soltura = []           # o que foi pedido ao confirm_released
        soltura_falha = False

    est = Estado()

    def sleep(_s):
        if est.interromper_no_segurar and (pg.apertado or kb.presas):
            est.interromper_no_segurar = False
            raise KeyboardInterrupt

    def confirm_released(names, *, timeout):
        est.soltura.append(tuple(names))
        if est.soltura_falha:
            raise InputReleaseError("preso")

    monkeypatch.setattr(modulo.time, "sleep", sleep)
    monkeypatch.setattr(modulo, "confirm_released", confirm_released)
    est.pg, est.kb = pg, kb
    return est


# --- construção ------------------------------------------------------------------


def test_with_pacing_pyautogui_pause_is_zero_and_failsafe_is_set(ambiente):
    PyAutoGuiDriver(pacing=RAPIDO, failsafe=True)
    assert ambiente.pg.PAUSE == 0.0 and ambiente.pg.FAILSAFE is True


def test_without_pacing_the_raw_pause_is_used(ambiente):
    PyAutoGuiDriver(pacing=None, pause=0.3)
    assert ambiente.pg.PAUSE == 0.3


# --- clique --------------------------------------------------------------------------


def test_click_aims_presses_releases_and_confirms(ambiente):
    PyAutoGuiDriver(pacing=RAPIDO).click(300, 200)
    assert ambiente.pg.calls == [("moveTo", 300, 200), ("down", "left"), ("up", "left", "com-coord", True)]
    assert ambiente.soltura == [("mouse_left",)]


@pytest.mark.parametrize("botao, esperado", [("right", "mouse_right"), ("secondary", "mouse_right"),
                                             ("middle", "mouse_middle"), ("primary", "mouse_left")])
def test_click_confirms_the_right_button(ambiente, botao, esperado):
    PyAutoGuiDriver(pacing=RAPIDO).click(1, 1, button=botao)
    assert ambiente.soltura == [(esperado,)]


def test_double_click_is_two_confirmed_presses(ambiente):
    PyAutoGuiDriver(pacing=RAPIDO).click(5, 5, clicks=2)
    assert [c[0] for c in ambiente.pg.calls if c[0] in ("down", "up")] == ["down", "up", "down", "up"]
    assert len(ambiente.soltura) == 2


def test_ctrl_c_while_holding_releases_the_button_without_moving_and_reraises(ambiente):
    ambiente.interromper_no_segurar = True
    with pytest.raises(KeyboardInterrupt):
        PyAutoGuiDriver(pacing=RAPIDO).click(300, 200)
    assert ambiente.pg.apertado is False
    assert ambiente.pg.calls[-1] == ("up", "left", "sem-mover", False)   # FAILSAFE desligado só na soltura
    assert ambiente.pg.FAILSAFE is True                                  # e religado depois


def test_failsafe_at_mouseup_still_releases_the_button(ambiente):
    ambiente.pg.mouseup_falha = FailSafe("mouse no canto")
    with pytest.raises(FailSafe):
        PyAutoGuiDriver(pacing=RAPIDO).click(300, 200)
    assert ambiente.pg.apertado is False
    assert ambiente.pg.FAILSAFE is True


def test_unconfirmed_release_names_the_button(ambiente):
    ambiente.soltura_falha = True
    with pytest.raises(InputReleaseError, match="botão 'left'"):
        PyAutoGuiDriver(pacing=RAPIDO).click(1, 1)


def test_without_pacing_click_is_the_raw_pyautogui_click(ambiente):
    PyAutoGuiDriver(pacing=None).click(7, 8, clicks=2)
    assert ambiente.pg.calls == [("click-cru", 7, 8, "left", 2)]


# --- teclado ---------------------------------------------------------------------------


def test_hotkey_presses_in_order_and_releases_in_reverse(ambiente):
    PyAutoGuiDriver(pacing=RAPIDO).hotkey("ctrl", "shift", "s")
    assert ambiente.kb.calls == [("press", "ctrl"), ("press", "shift"), ("press", "s"),
                                 ("release", "s"), ("release", "shift"), ("release", "ctrl")]


def test_ctrl_c_in_the_middle_of_a_hotkey_releases_what_was_pressed(ambiente):
    ambiente.interromper_no_segurar = True       # interrompe logo depois do 1º press
    with pytest.raises(KeyboardInterrupt):
        PyAutoGuiDriver(pacing=RAPIDO).hotkey("ctrl", "shift", "s")
    assert ambiente.kb.presas == set()            # nada preso na máquina
    assert ("press", "shift") not in ambiente.kb.calls


def test_a_key_the_os_never_releases_raises(ambiente):
    ambiente.kb.nunca_solta = {"shift"}
    with pytest.raises(InputReleaseError, match="shift"):
        PyAutoGuiDriver(pacing=RAPIDO).press("shift")


def test_without_pacing_keys_are_sent_raw(ambiente):
    d = PyAutoGuiDriver(pacing=None)
    d.press("enter")
    d.hotkey("ctrl", "s")
    assert ambiente.kb.calls == [("send", "enter"), ("send", "ctrl+s")]


def test_write_with_pacing_types_one_char_at_a_time(ambiente):
    PyAutoGuiDriver(pacing=RAPIDO).write("ab")
    assert ambiente.kb.calls == [("write", "a"), ("write", "b")]


def test_write_without_pacing_and_no_delay_types_at_once(ambiente):
    PyAutoGuiDriver(pacing=None).write("abc")
    assert ambiente.kb.calls == [("write", "abc")]


# --- arrasto ---------------------------------------------------------------------------


def test_drag_goes_to_start_drags_and_confirms(ambiente):
    PyAutoGuiDriver(pacing=RAPIDO).drag((10, 10), (90, 10))
    assert ambiente.pg.calls == [("moveTo", 10, 10), ("dragTo", 90, 10)]
    assert ambiente.soltura == [("mouse_left",)]


def test_interrupted_drag_releases_the_button(ambiente):
    ambiente.pg.drag_falha = FailSafe("canto no meio do trajeto")
    with pytest.raises(FailSafe):
        PyAutoGuiDriver(pacing=RAPIDO).drag((10, 10), (90, 10))
    assert ambiente.pg.apertado is False
    assert ambiente.pg.calls[-1] == ("up", "left", "sem-mover", False)


# --- leitura ---------------------------------------------------------------------------


def test_cursor_and_key_state_and_screen(ambiente):
    d = PyAutoGuiDriver(pacing=RAPIDO)
    ambiente.pg.pos = (12.0, 34.0)
    ambiente.kb.presas = {"esc"}
    assert d.cursor_position() == (12, 34)
    assert d.is_key_down("esc") is True and d.is_key_down("shift") is False
    assert d.screen_size() == (1366, 768)
    assert d.screenshot((1, 2, 3, 4)) == ("tela", (1, 2, 3, 4))


# --- template --------------------------------------------------------------------------


def _png(caminho):
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    ok, buf = cv2.imencode(".png", np.full((6, 8, 3), 200, dtype=np.uint8))
    assert ok
    buf.tofile(str(caminho))
    return caminho


def test_missing_template_is_a_clear_error_not_a_timeout(ambiente, tmp_path):
    with pytest.raises(FileNotFoundError, match="nao_existe.png"):
        PyAutoGuiDriver(pacing=RAPIDO).locate_on_screen(str(tmp_path / "nao_existe.png"))


def test_unreadable_template_is_a_locator_error(ambiente, tmp_path):
    pytest.importorskip("cv2")
    lixo = tmp_path / "lixo.png"
    lixo.write_bytes(b"isto nao e uma imagem")
    with pytest.raises(LocatorError, match="ilegível"):
        PyAutoGuiDriver(pacing=RAPIDO).locate_on_screen(str(lixo))


def test_template_under_an_accented_path_is_loaded_and_found(ambiente, tmp_path):
    np = pytest.importorskip("numpy")
    caminho = _png(tmp_path / "Conteúdo" / "matérias" / "botão.png")
    ambiente.pg.achado = (100, 200, 20, 10)

    pos = PyAutoGuiDriver(pacing=RAPIDO).locate_on_screen(str(caminho))

    assert pos == (110.0, 205.0)
    assert isinstance(ambiente.pg.agulha, np.ndarray)   # a imagem já carregada, não o caminho


def test_not_found_at_exact_size_falls_back_to_multi_scale_with_the_same_image(ambiente, tmp_path, monkeypatch):
    np = pytest.importorskip("numpy")
    from prumo.drivers import _template_match

    caminho = _png(tmp_path / "t.png")
    recebido = {}

    def multi(screen, template, *, confidence):
        recebido["template"] = template
        return (1.0, 2.0)

    monkeypatch.setattr(_template_match, "locate_multi_scale", multi)
    monkeypatch.setattr(ambiente.pg, "screenshot", lambda region=None: np.zeros((4, 4, 3), dtype=np.uint8))

    assert PyAutoGuiDriver(pacing=RAPIDO).locate_on_screen(str(caminho)) == (1.0, 2.0)
    assert recebido["template"] is ambiente.pg.agulha    # leu o arquivo UMA vez


# --- DPI awareness ----------------------------------------------------------------------


class _Lib:
    def __init__(self, **funcs):
        self.__dict__.update(funcs)


def _windll(*, aware, shcore_falha=True):
    def shcore_set(_v):
        if shcore_falha:
            raise AttributeError("sem shcore")

    return _Lib(shcore=_Lib(SetProcessDpiAwareness=shcore_set),
                user32=_Lib(SetProcessDPIAware=lambda: 1, IsProcessDPIAware=lambda: aware))


def test_dpi_unaware_process_is_warned_not_silent(monkeypatch, caplog):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(ctypes, "windll", _windll(aware=0), raising=False)
    with caplog.at_level(logging.WARNING, logger="prumo"):
        PyAutoGuiDriver._ensure_dpi_awareness()
    assert any("DPI-aware" in r.getMessage() for r in caplog.records)


def test_dpi_aware_process_says_nothing(monkeypatch, caplog):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(ctypes, "windll", _windll(aware=1, shcore_falha=False), raising=False)
    with caplog.at_level(logging.WARNING, logger="prumo"):
        PyAutoGuiDriver._ensure_dpi_awareness()
    assert caplog.records == []
