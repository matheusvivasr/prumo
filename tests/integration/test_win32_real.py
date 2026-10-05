"""As consultas finas ao Win32, contra o Windows de verdade — SÓ LEITURA.

Unitariamente elas não têm o que testar (são uma chamada ao SO cada). O risco
real é de declaração: um `restype` errado no ctypes trunca o handle em 64 bits
e o gate passa a comparar janelas erradas sem erro nenhum. Só rodando contra o
SO isso aparece. Nada aqui mexe em mouse ou teclado; sem janela visível (CI
sem área de trabalho) os testes são pulados, não reprovados.
"""

from __future__ import annotations

import sys

import pytest

pytestmark = [
    pytest.mark.win32_real,
    pytest.mark.skipif(sys.platform != "win32", reason="consulta o Win32 real"),
]


def _janela_visivel():
    import pygetwindow as gw

    for w in gw.getAllWindows():
        try:
            if w.title.strip() and w.visible and not w.isMinimized and w.width > 80 and w.height > 80:
                return w
        except Exception:  # noqa: BLE001 - janela fechando durante a varredura: só pula
            continue
    pytest.skip("nenhuma janela de topo visível nesta sessão")


def test_pid_of_a_real_top_level_window_is_known():
    from prumo.drivers.window import WindowManager

    w = _janela_visivel()
    assert WindowManager._pid(w._hWnd) > 0


def test_a_top_level_window_is_its_own_root_and_handles_round_trip():
    from prumo.drivers.window import WindowManager

    w = _janela_visivel()
    raiz = WindowManager._root_ancestor(w._hWnd)
    assert raiz == int(w._hWnd)                         # handle inteiro, sem truncar
    assert WindowManager._root_ancestor(raiz) == raiz


def test_window_from_point_returns_a_real_window_with_a_process():
    from prumo.drivers.window import WindowManager

    w = _janela_visivel()
    cx, cy = w.left + w.width // 2, w.top + w.height // 2
    hwnd = WindowManager._window_from_point(cx, cy)
    assert hwnd > 0
    raiz = WindowManager._root_ancestor(hwnd)
    assert raiz > 0 and WindowManager._pid(raiz) > 0     # é DE alguém, ainda que outra janela esteja por cima


def test_foreground_window_query_answers_an_integer():
    from prumo.drivers.window import WindowManager

    frente = WindowManager._foreground_hwnd()
    assert isinstance(frente, int) and frente >= 0       # 0 é legítimo (transição, sessão sem área de trabalho)


def test_owns_point_agrees_with_the_os_on_a_real_window():
    from prumo.drivers.window import WindowManager

    w = _janela_visivel()
    cx, cy = w.left + w.width // 2, w.top + w.height // 2
    m = WindowManager(title=w.title, exact=True)
    m._window = w
    dono = WindowManager._root_ancestor(WindowManager._window_from_point(cx, cy))
    mesmo_processo = WindowManager._pid(dono) == WindowManager._pid(w._hWnd)
    assert m.owns_point(cx, cy) is (dono == int(w._hWnd) or mesmo_processo)


def test_release_query_reads_real_key_state():
    from prumo.drivers.release import held_inputs

    assert isinstance(held_inputs(), list)               # o conteúdo depende de quem está no teclado


def test_real_windows_ocr_reads_accented_text_and_normalize_folds_it():
    pytest.importorskip("winocr")
    from PIL import Image, ImageDraw, ImageFont

    from prumo.core.exceptions import UnexpectedStateError
    from prumo.drivers.ocr import normalize, read_lines

    img = Image.new("RGB", (360, 50), "white")
    try:
        fonte = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        pytest.skip("sem a fonte Arial para desenhar o texto")
    ImageDraw.Draw(img).text((10, 10), "Função Configurações", fill="black", font=fonte)
    try:
        linhas = read_lines(img)
    except UnexpectedStateError as exc:     # Windows sem o pacote de OCR pt-BR (ex.: runner em inglês)
        pytest.skip(str(exc))
    assert [normalize(tl.text) for tl in linhas] == ["funcaoconfiguracoes"]
