"""drivers/ocr — leitura de texto (ARCHITECTURE.md §9.11).

O `winocr` é trocado por um dublê que devolve linhas/palavras com caixas,
como o OCR do Windows: o que se testa é a conversão de coordenadas, o
tratamento de erro e a normalização — não o OCR em si (esse fica no teste
`win32_real` de tests/integration).
"""

from __future__ import annotations

import asyncio
import sys
from types import SimpleNamespace

import pytest

from prumo.core.exceptions import UnexpectedStateError
from prumo.drivers import ocr

Image = pytest.importorskip("PIL.Image")


def _palavra(x, y, w, h):
    return SimpleNamespace(bounding_rect=SimpleNamespace(x=x, y=y, width=w, height=h))


def _winocr_falso(monkeypatch, *, linhas=(), erro=None):
    recebido = {}

    async def recognize_pil(img, lang):
        recebido["tamanho"], recebido["lang"] = img.size, lang
        if erro is not None:
            raise erro
        return SimpleNamespace(lines=list(linhas))

    monkeypatch.setitem(sys.modules, "winocr", SimpleNamespace(recognize_pil=recognize_pil))
    return recebido


def test_boxes_come_back_in_the_original_image_coordinates_plus_offset(monkeypatch):
    # o OCR vê a imagem ampliada 3x; a caixa tem de voltar na escala original
    linha = SimpleNamespace(text="RESUMO", words=[_palavra(30, 60, 90, 30), _palavra(150, 63, 60, 27)])
    recebido = _winocr_falso(monkeypatch, linhas=[linha])

    (tl,) = ocr.read_lines(Image.new("RGB", (100, 40)), offset=(500, 200))

    assert recebido["tamanho"] == (300, 120) and recebido["lang"] == "pt-BR"
    assert (tl.text, tl.x, tl.y, tl.w, tl.h) == ("RESUMO", 510.0, 220.0, 60.0, 10.0)
    assert tl.cy == 225.0


def test_lines_without_words_are_skipped(monkeypatch):
    _winocr_falso(monkeypatch, linhas=[SimpleNamespace(text="", words=[])])
    assert ocr.read_lines(Image.new("RGB", (10, 10))) == []


def test_missing_language_pack_is_a_clear_error(monkeypatch):
    _winocr_falso(monkeypatch, erro=AssertionError("Add-WindowsCapability -Online -Name Language.OCR~~~pt-BR"))
    with pytest.raises(UnexpectedStateError, match="não tem o idioma 'pt-BR'.*Add-WindowsCapability"):
        ocr.read_lines(Image.new("RGB", (10, 10)))


def test_reading_from_inside_a_running_event_loop_works(monkeypatch):
    # asyncio.run dentro de um loop rodando levantaria RuntimeError (Jupyter, app assíncrono)
    _winocr_falso(monkeypatch, linhas=[SimpleNamespace(text="OK", words=[_palavra(0, 0, 3, 3)])])

    async def app():
        return ocr.read_lines(Image.new("RGB", (10, 10)))

    assert [tl.text for tl in asyncio.run(app())] == ["OK"]


@pytest.mark.parametrize(
    "texto, esperado",
    [("Função", "funcao"), ("Configurações", "configuracoes"), ("Conteúdo_2", "conteudo2"), ("SET0188", "set0188")],
)
def test_normalize_folds_accents_instead_of_dropping_letters(texto, esperado):
    assert ocr.normalize(texto) == esperado


def test_ocr_reading_without_accents_matches_the_accented_label():
    # antes: 0,8 ("Função" virava "funo")
    assert ocr.similarity("Funcao", "Função") == 1.0
    assert ocr.similarity("Configuracoes", "Configurações") == 1.0
    assert ocr.similarity("Funcao", "Matriz") < 0.5
