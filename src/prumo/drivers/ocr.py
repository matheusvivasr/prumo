"""OCR como capacidade opcional do driver — ARCHITECTURE.md §9.11.

Lê texto de uma imagem PIL com o OCR nativo do Windows (`Windows.Media.Ocr`,
via `winocr`, extra `[ocr]`). É instrumento de **leitura**: não interage com a
aplicação. Achado (hp-prime-automation, 29/09/2026): lê bem telas de bitmap da
HP Prime ampliadas 3x, mas erra caracteres parecidos (0/O, _ ...) — quem usa
compara com `similarity` e sempre CONFERE o estado depois (§9.9).

Custo: cada chamada é ~0,3 s. Use só onde a leitura é o próprio objetivo
(escolher por nome, ler um resultado); para estado conhecido prefira template
(§9.2) ou cor (§9.3), que são mais baratos."""

from __future__ import annotations

import asyncio
import difflib
import re
from dataclasses import dataclass
from typing import List, Tuple

_SCALE = 3


@dataclass(frozen=True)
class TextLine:
    text: str
    x: float  # coordenadas na imagem ORIGINAL (divididas pela escala + offset)
    y: float
    w: float
    h: float

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


def read_lines(img, *, offset: Tuple[int, int] = (0, 0), lang: str = "pt-BR") -> List[TextLine]:
    """OCR de uma imagem PIL; uma `TextLine` por linha, com a caixa no sistema
    de coordenadas de `img` (+ `offset`, para recortes)."""
    import winocr
    from PIL import Image

    big = img.resize((img.width * _SCALE, img.height * _SCALE), Image.LANCZOS)

    async def _run():
        # `winocr` devolve um objeto assíncrono do WinRT, não uma corrotina:
        # `asyncio.run(winocr.recognize_pil(...))` direto levanta ValueError.
        return await winocr.recognize_pil(big, lang)

    res = asyncio.run(_run())
    out: List[TextLine] = []
    for ln in res.lines:
        if not ln.words:
            continue
        x0 = min(w.bounding_rect.x for w in ln.words)
        y0 = min(w.bounding_rect.y for w in ln.words)
        x1 = max(w.bounding_rect.x + w.bounding_rect.width for w in ln.words)
        y1 = max(w.bounding_rect.y + w.bounding_rect.height for w in ln.words)
        out.append(
            TextLine(
                ln.text,
                offset[0] + x0 / _SCALE,
                offset[1] + y0 / _SCALE,
                (x1 - x0) / _SCALE,
                (y1 - y0) / _SCALE,
            )
        )
    return out


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def similarity(a: str, b: str) -> float:
    """0..1, ignorando caixa e pontuação (tolerante ao que o OCR confunde)."""
    return difflib.SequenceMatcher(None, normalize(a), normalize(b)).ratio()
