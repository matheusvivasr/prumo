"""InterruptionManager — popups tratados E conferidos fora da tela (ARCHITECTURE.md §12).

Até 05/10/2026 o manager chamava `handle()` e seguia, sem conferir que o popup
tinha saído: um "OK" que não fechava deixava a ação seguinte cair no popup.
Os dublês aqui são popups de verdade: `handle()` só fecha se `fecha=True`.
"""

import pytest

from prumo.core.events import Interruption, InterruptionManager
from prumo.core.exceptions import PopupError


class Popup:
    def __init__(self, nome, *, aberto=True, fecha=True):
        self.nome, self.aberto, self.fecha = nome, aberto, fecha
        self.tratado = 0

    def detect(self):
        return self.aberto

    def handle(self):
        self.tratado += 1
        if self.fecha:
            self.aberto = False

    def como_interrupcao(self):
        return Interruption(name=self.nome, detect=self.detect, handle=self.handle)


def manager(*popups, **kw):
    m = InterruptionManager(confirm_timeout=0.05, **kw)
    for p in popups:
        m.register(p.como_interrupcao())
    return m


def test_no_interruption_detected_returns_none():
    assert manager(Popup("popup", aberto=False)).check_and_handle() is None


def test_a_present_popup_is_handled_and_confirmed_gone():
    p = Popup("erro de sintaxe")
    assert manager(p).check_and_handle().name == "erro de sintaxe"
    assert p.tratado == 1 and p.aberto is False


def test_stacked_popups_are_all_handled_in_registration_order():
    # antes: só o primeiro era tratado e a ação seguia com o segundo na tela
    a, b, c = Popup("a", aberto=False), Popup("b"), Popup("c")
    resultado = manager(a, b, c).check_and_handle()
    assert (a.tratado, b.tratado, c.tratado) == (0, 1, 1)
    assert resultado.name == "c"


def test_a_popup_the_handler_does_not_close_is_an_error():
    # o "OK" clicado no lugar errado: o popup continua — nenhuma ação pode seguir
    teimoso = Popup("salvar alterações?", fecha=False)
    with pytest.raises(PopupError, match="continua presente"):
        manager(teimoso).check_and_handle()


def test_a_popup_that_keeps_coming_back_is_an_error_not_a_loop():
    leituras = iter([True, False] * 10)      # aparece, some depois do OK, aparece de novo...
    tratados = []
    m = InterruptionManager(confirm_timeout=0.05, max_rounds=3)
    m.register(Interruption(name="aviso", detect=lambda: next(leituras), handle=lambda: tratados.append(1)))
    with pytest.raises(PopupError, match="reaparece"):
        m.check_and_handle()
    assert len(tratados) == 3                 # tratou o limite e parou, sem laço eterno
