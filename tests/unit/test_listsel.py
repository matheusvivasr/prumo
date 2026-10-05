"""ListSelector: lógica de selecionar por nome, sem GUI (lista falsa)."""

import pytest

from prumo.core.listsel import AmbiguousItemError, ItemNotFoundError, ListSelector, Row


class ListaFalsa:
    """Lista vertical com janela visível de `visiveis` linhas e destaque móvel."""

    def __init__(self, itens, *, visiveis=4, destaque=0):
        self.itens, self.visiveis, self.i, self.topo = itens, visiveis, destaque, 0
        self.teclas = []

    def rows(self):
        self.topo = min(max(self.topo, self.i - self.visiveis + 1), self.i) if not (self.topo <= self.i < self.topo + self.visiveis) else self.topo
        return [
            Row(t, cy=20.0 * (k - self.topo), selected=(k == self.i))
            for k, t in enumerate(self.itens)
            if self.topo <= k < self.topo + self.visiveis
        ]

    def down(self):
        self.teclas.append("down")
        self.i = min(self.i + 1, len(self.itens) - 1)

    def up(self):
        self.teclas.append("up")
        self.i = max(self.i - 1, 0)


def seletor(lista, **kw):
    return ListSelector(read_rows=lista.rows, move_down=lista.down, move_up=lista.up, settle_s=0, **kw)


def test_ja_destacado_nao_gasta_tecla():
    l = ListaFalsa(["Funcao (App)", "SET0188_Menu", "Outro"], destaque=1)
    assert seletor(l).select("SET0188_Menu") == 0 and l.teclas == []


def test_desce_ate_o_alvo_visivel():
    l = ListaFalsa(["A_um", "B_dois", "C_tres", "D_quatro"])
    assert seletor(l).select("C_tres") == 2 and l.teclas == ["down", "down"]


def test_sobe_quando_o_alvo_esta_acima():
    l = ListaFalsa(["A_um", "B_dois", "C_tres", "D_quatro"], destaque=3)
    assert seletor(l).select("B_dois") == 2 and l.teclas == ["up", "up"]


def test_rola_quando_o_alvo_esta_fora_da_janela_visivel():
    itens = [f"Prog_{c}" for c in "abcdefghij"]
    l = ListaFalsa(itens, visiveis=3)
    assert seletor(l).select("Prog_h") > 0 and l.itens[l.i] == "Prog_h"


def test_tolera_confusao_do_ocr_entre_0_e_O():
    l = ListaFalsa(["Funcao", "SET0188_Menu", "Zeta"], destaque=0)
    assert seletor(l).select("SET0188_Menu") == 1
    l2 = ListaFalsa(["Funcao", "SETO188_Menu", "Zeta"], destaque=0)  # OCR leu 0 como O
    assert seletor(l2, min_similarity=0.85).select("SET0188_Menu") == 1


def test_ambiguo_para_em_vez_de_chutar():
    l = ListaFalsa(["SET0188_TrelicaNos", "SET0188_TrelicaNo2", "Zeta"])
    with pytest.raises(AmbiguousItemError):
        seletor(l).select("SET0188_TrelicaNo")  # sem casamento exato: os dois empatam


def test_casamento_exato_vence_um_quase_igual():
    l = ListaFalsa(["SET0188_TrelicaNos", "SET0188_TrelicaNo2", "Zeta"], destaque=1)
    assert seletor(l).select("SET0188_TrelicaNos") == 1


def test_inexistente_estoura_o_limite_e_chama_on_fail():
    l = ListaFalsa(["A_um", "B_dois"])
    falhas = []
    with pytest.raises(ItemNotFoundError):
        seletor(l, max_steps=5, on_fail=falhas.append).select("Nao_existe")
    assert falhas == ["lista_sem_Nao_existe"]


def test_alvo_acima_do_trecho_visivel_e_achado_dando_a_volta():
    # a lista abriu no MEIO (destaque num item de baixo): o alvo está acima da
    # parte visível. Antes: só descia, batia no fim e dizia "não achei".
    itens = [f"Prog_{c}" for c in "abcdefghij"]
    l = ListaFalsa(itens, visiveis=3, destaque=6)
    teclas = seletor(l).select("Prog_b")
    assert l.itens[l.i] == "Prog_b" and teclas > 0
    assert "up" in l.teclas


def test_lista_percorrida_nos_dois_sentidos_sem_o_item_sai_antes_do_limite():
    l = ListaFalsa([f"Prog_{c}" for c in "abcdef"], visiveis=3, destaque=2)
    falhas = []
    with pytest.raises(ItemNotFoundError, match="dois sentidos"):
        seletor(l, max_steps=60, on_fail=falhas.append).select("Nao_existe")
    assert len(l.teclas) < 60 and falhas == ["lista_sem_Nao_existe"]


def test_uma_leitura_repetida_so_nao_inverte_o_sentido():
    # app lento: a lista não redesenhou a tempo UMA vez — não é fim de lista
    itens = [f"Prog_{c}" for c in "abcdefgh"]
    l = ListaFalsa(itens, visiveis=3)
    lento = {"vezes": 1}
    original = l.down

    def down_lento():
        if lento["vezes"]:
            lento["vezes"] -= 1
            l.teclas.append("down")     # a tecla saiu, mas a tela não mudou ainda
            return
        original()

    sel = ListSelector(read_rows=l.rows, move_down=down_lento, move_up=l.up, settle_s=0)
    sel.select("Prog_g")
    assert l.itens[l.i] == "Prog_g" and "up" not in l.teclas
