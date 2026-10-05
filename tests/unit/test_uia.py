"""UiaWindow — achar, ler e conferir ponto por UI Automation (ARCHITECTURE.md §9.13).

O módulo `uiautomation` é trocado por `FakeAuto`, que imita só a superfície
que a `UiaWindow` usa. O que se testa é a decisão (qual janela, qual processo,
o que conta como visível), não a UIA do Windows.
"""

from __future__ import annotations

import pytest

from prumo.core.exceptions import AutomationTimeoutError, UnexpectedStateError, WindowNotFoundError
from prumo.drivers.uia import UiaWindow


class Rect:
    def __init__(self, left, top, right, bottom):
        self.left, self.top, self.right, self.bottom = left, top, right, bottom

    def width(self):
        return self.right - self.left

    def height(self):
        return self.bottom - self.top


class Valor:
    def __init__(self, value):
        self.Value = value


class Ctrl:
    def __init__(self, *, pid=7, rect=(0, 0, 10, 10), value="", children=(), **props):
        self.ProcessId = pid
        self.BoundingRectangle = Rect(*rect)
        self.props = props
        self.children = list(children)
        self._value = value
        self.vivo = True

    def Exists(self, timeout=0, interval=0):
        return self.vivo

    def GetValuePattern(self):
        return Valor(self._value)

    def matches(self, props):
        return all(self.props.get(k) == v for k, v in props.items())

    def walk(self):
        for c in self.children:
            yield c
            yield from c.walk()


class Missing:
    """O que a UIA devolve quando nada casa: um controle cujo Exists é False."""

    def Exists(self, timeout=0, interval=0):
        return False


class FakeAuto:
    def __init__(self, tops=(), at_point=None, point_errors=0):
        self.tops = list(tops)
        self.at_point = at_point
        self.point_errors = point_errors
        self.point_calls = 0

    def WindowControl(self, searchDepth=1, Compare=None, **props):
        for w in self.tops:
            if w.vivo and w.matches(props) and (Compare is None or Compare(w, 1)):
                return w
        return Missing()

    def Control(self, searchFromControl, **props):
        for c in searchFromControl.walk():
            if c.matches(props):
                return c
        return Missing()

    def ControlFromPoint(self, x, y):
        self.point_calls += 1
        if self.point_errors:
            self.point_errors -= 1
            raise OSError("COMError intermitente")
        return self.at_point


def kit_like():
    """Uma janela de topo com dois controles: um visível e um 'Collapsed'."""
    ok = Ctrl(AutomationId="btn-ok", rect=(100, 200, 140, 220))
    escondido = Ctrl(AutomationId="painel-x", rect=(0, 0, 0, 0))
    campo = Ctrl(AutomationId="campo", value="texto atual")
    janela = Ctrl(pid=7, Name="Painel", ClassName="CConKitApp", children=[ok, escondido, campo])
    return janela, ok, escondido, campo


# --- janela -------------------------------------------------------------------


def test_needs_name_or_class_name():
    with pytest.raises(ValueError):
        UiaWindow()


def test_connect_by_class_name_takes_the_pid_from_the_window():
    # o caminho do hp-prime-CK: acha pela classe, descobre o processo depois
    janela, *_ = kit_like()
    w = UiaWindow(class_name="CConKitApp", backend=FakeAuto([janela])).connect()
    assert w.pid == 7


def test_a_fixed_pid_skips_another_instance_with_the_same_title():
    # o caminho do e2e da Tina: foi ela quem abriu o processo 8
    outra = Ctrl(pid=7, Name="Painel")
    minha = Ctrl(pid=8, Name="Painel")
    w = UiaWindow(name="Painel", pid=8, backend=FakeAuto([outra, minha])).connect()
    assert w.root is minha


def test_connect_raises_when_only_another_process_has_the_window():
    outra = Ctrl(pid=7, Name="Painel")
    with pytest.raises(WindowNotFoundError, match="pid=8"):
        UiaWindow(name="Painel", pid=8, backend=FakeAuto([outra])).connect(timeout=0)


def test_root_before_connect_is_a_programming_error():
    with pytest.raises(UnexpectedStateError, match="connect"):
        _ = UiaWindow(name="Painel", backend=FakeAuto()).root


def test_root_does_not_silently_bind_to_a_new_instance_when_pid_is_fixed():
    minha = Ctrl(pid=8, Name="Painel")
    auto = FakeAuto([minha])
    w = UiaWindow(name="Painel", pid=8, backend=auto).connect()
    minha.vivo = False                       # o app fechou...
    auto.tops.append(Ctrl(pid=9, Name="Painel"))  # ...e abriu de novo, noutro processo
    with pytest.raises(WindowNotFoundError):
        _ = w.root


# --- achar e ler ----------------------------------------------------------------


def test_find_returns_the_control():
    janela, ok, *_ = kit_like()
    w = UiaWindow(class_name="CConKitApp", backend=FakeAuto([janela])).connect()
    assert w.find(AutomationId="btn-ok") is ok


def test_find_names_what_it_was_looking_for_when_it_times_out():
    janela, *_ = kit_like()
    w = UiaWindow(class_name="CConKitApp", backend=FakeAuto([janela])).connect()
    with pytest.raises(AutomationTimeoutError, match="btn-cancelar"):
        w.find(AutomationId="btn-cancelar", timeout=0)


def test_is_visible_needs_area_not_just_presence_in_the_tree():
    janela, *_ = kit_like()
    w = UiaWindow(class_name="CConKitApp", backend=FakeAuto([janela])).connect()
    assert w.is_visible(AutomationId="btn-ok") is True
    assert w.is_visible(AutomationId="painel-x") is False      # Collapsed: na árvore, área zero
    assert w.is_visible(AutomationId="nao-existe") is False


def test_center_is_the_middle_of_the_bounding_rectangle():
    janela, ok, *_ = kit_like()
    w = UiaWindow(class_name="CConKitApp", backend=FakeAuto([janela])).connect()
    assert w.center(ok) == (120, 210)


def test_center_refuses_a_control_without_area():
    janela, _, escondido, _ = kit_like()
    w = UiaWindow(class_name="CConKitApp", backend=FakeAuto([janela])).connect()
    with pytest.raises(UnexpectedStateError, match="sem área"):
        w.center(escondido, "painel-x")


def test_value_reads_the_value_pattern():
    janela, *_, campo = kit_like()
    w = UiaWindow(class_name="CConKitApp", backend=FakeAuto([janela])).connect()
    assert w.value(campo) == "texto atual"


# --- conferir ponto ---------------------------------------------------------------


def make_point_window(**auto_kwargs):
    janela, *_ = kit_like()
    auto = FakeAuto([janela], **auto_kwargs)
    return UiaWindow(class_name="CConKitApp", backend=auto).connect(), auto


def test_owns_point_when_the_control_there_is_from_the_same_process():
    w, _ = make_point_window(at_point=Ctrl(pid=7))
    assert w.owns_point(120, 210) is True


def test_does_not_own_point_covered_by_another_process():
    w, _ = make_point_window(at_point=Ctrl(pid=99))
    assert w.owns_point(120, 210) is False


def test_does_not_own_point_when_nothing_is_there():
    w, _ = make_point_window(at_point=None)
    assert w.owns_point(120, 210) is False


def test_owns_point_retries_once_on_an_intermittent_error():
    w, auto = make_point_window(at_point=Ctrl(pid=7), point_errors=1)
    assert w.owns_point(120, 210) is True
    assert auto.point_calls == 2


def test_owns_point_lets_a_persistent_error_surface():
    w, _ = make_point_window(at_point=Ctrl(pid=7), point_errors=2)
    with pytest.raises(OSError):
        w.owns_point(120, 210)
