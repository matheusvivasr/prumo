"""Testes de `locate_multi_scale` com arrays sintéticos — sem tela real,
sem PyAutoGuiDriver. Prova que a busca multi-escala acha um template
mesmo quando a "aplicação" o renderizou em outro tamanho (o achado real
de 25/08/2026: mesmo botão, dois modos de layout da HP Prime, tamanhos
diferentes)."""

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2", reason="locate_multi_scale exige opencv-python")

from prumo.drivers._template_match import locate_multi_scale  # noqa: E402


def _tela_com_alvo(alvo, pos, tamanho_tela=(200, 200)):
    """Fundo cinza uniforme com `alvo` colado em `pos` (top-left)."""
    tela = np.full((*tamanho_tela, 3), 128, dtype=np.uint8)
    h, w = alvo.shape[:2]
    y, x = pos
    tela[y : y + h, x : x + w] = alvo
    return tela


def _template_distinto(tamanho=32):
    """Um padrão com bastante contraste interno (não um bloco de cor
    sólida — matchTemplate com bloco sólido "casa" em qualquer lugar do
    fundo uniforme, o que mascararia bug de posição/escala)."""
    t = np.zeros((tamanho, tamanho, 3), dtype=np.uint8)
    t[:, :, 0] = 40
    t[: tamanho // 2, : tamanho // 2] = (220, 30, 30)
    t[tamanho // 2 :, tamanho // 2 :] = (30, 220, 30)
    return t


def test_finds_template_at_exact_scale():
    template = _template_distinto(32)
    tela = _tela_com_alvo(template, pos=(50, 60))

    centro = locate_multi_scale(tela, template, confidence=0.85)

    assert centro is not None
    cx, cy = centro
    assert abs(cx - (60 + 16)) <= 1  # x = left + w/2
    assert abs(cy - (50 + 16)) <= 1


def test_finds_template_rendered_smaller():
    """O caso real: o mesmo botão, só que menor (~75% do tamanho
    original) — locateOnScreen de escala única não acharia isso."""
    template = _template_distinto(32)
    menor = cv2.resize(template, (24, 24))  # 75% de 32
    tela = _tela_com_alvo(menor, pos=(50, 60))

    centro = locate_multi_scale(tela, template, confidence=0.85, scales=(0.7, 0.75, 0.8, 1.0))

    assert centro is not None
    cx, cy = centro
    assert abs(cx - (60 + 12)) <= 2
    assert abs(cy - (50 + 12)) <= 2


def test_returns_none_when_template_absent():
    template = _template_distinto(32)
    tela = np.full((200, 200, 3), 128, dtype=np.uint8)  # fundo liso, sem o alvo

    assert locate_multi_scale(tela, template, confidence=0.85) is None


def test_returns_none_when_confidence_too_strict_for_any_scale():
    template = _template_distinto(32)
    menor = cv2.resize(template, (24, 24))
    tela = _tela_com_alvo(menor, pos=(50, 60))

    # so testa escalas que nao batem o tamanho real (24/32=0.75) -> nenhuma fecha bem
    centro = locate_multi_scale(tela, template, confidence=0.99, scales=(1.0,))

    assert centro is None
