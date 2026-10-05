"""`WindowManager._esta_ativa` tolera `isActive` levantando (janela em transição)."""

from prumo.drivers.window import WindowManager


class _Janela:
    def __init__(self, respostas):
        self._respostas = list(respostas)

    @property
    def isActive(self):
        r = self._respostas.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def test_repete_quando_isactive_levanta_e_devolve_o_valor_seguinte():
    assert WindowManager._esta_ativa(_Janela([RuntimeError("1400"), RuntimeError("1400"), True])) is True


def test_devolve_false_se_persistir_o_erro():
    assert WindowManager._esta_ativa(_Janela([RuntimeError("x")] * 5), tentativas=5) is False
