"""Casamento de template multi-escala — implementação de `PyAutoGuiDriver.
locate_on_screen`, não parte da API pública do `prumo`.

`pyautogui.locateOnScreen` sozinho testa só o tamanho exato do template —
se o botão renderizar em outro tamanho (ex.: a mesma aplicação com um
layout diferente, que não só reposiciona como redimensiona os elementos),
a confiança despenca mesmo com o botão visível e correto na tela (achado
real: 25/08/2026, HP Prime — mesmo template, dois modos de layout,
confiança foi de >0.85 pra 0.436 num deles). Este módulo tenta várias
escalas do template e fica com a que casar melhor.
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

DEFAULT_SCALES: Tuple[float, ...] = (0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15, 1.2)


def locate_multi_scale(
    screen_bgr,
    template_bgr,
    *,
    confidence: float = 0.85,
    scales: Sequence[float] = DEFAULT_SCALES,
) -> Optional[Tuple[float, float]]:
    """Centro (x, y) do melhor casamento de `template_bgr` em `screen_bgr`,
    testando `scales` do template. `None` se nenhuma escala bater
    `confidence`. Arrays no formato do OpenCV (BGR, `numpy.ndarray`).
    """
    import cv2

    th, tw = template_bgr.shape[:2]
    sh, sw = screen_bgr.shape[:2]

    melhor_valor = -1.0
    melhor_loc: Optional[Tuple[int, int]] = None
    melhor_wh: Optional[Tuple[int, int]] = None

    for escala in scales:
        w, h = max(1, round(tw * escala)), max(1, round(th * escala))
        if w > sw or h > sh:
            continue
        candidato = cv2.resize(template_bgr, (w, h)) if escala != 1.0 else template_bgr
        resultado = cv2.matchTemplate(screen_bgr, candidato, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(resultado)
        if max_val > melhor_valor:
            melhor_valor, melhor_loc, melhor_wh = max_val, max_loc, (w, h)

    if melhor_valor < confidence or melhor_loc is None or melhor_wh is None:
        return None

    left, top = melhor_loc
    w, h = melhor_wh
    return left + w / 2, top + h / 2
