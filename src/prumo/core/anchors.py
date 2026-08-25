"""Resolução de locator por âncoras de imagem — ARCHITECTURE.md §6.1.

Coordenadas relativas à janela (§2.3, §27) pressupõem que a aplicação
inteira escala e move como um retângulo rígido a partir de
`window.geometry()`. Duas coisas quebram essa suposição na prática:

1. **`window.geometry()` não bate com o conteúdo renderizado.** O
   retângulo "lógico" que o SO reporta pode divergir dos pixels reais
   (observado com DPI — ver `hp-prime-automation`, onde um teclado
   calibrado por fração de `window.geometry()` precisava de uma largura
   ~4-9% maior que a janela reportava pra fechar a conta).
2. **A aplicação tem mais de um MODO DE LAYOUT.** Uma janela redimensionada
   pode reorganizar a interface (não só escalar) — coordenadas calibradas
   num modo não generalizam pro outro nem multiplicando por uma razão de
   escala.

`AnchorZone` contorna os dois: localiza 2 pontos de referência **direto na
tela**, por casamento de imagem (`InputDriver.locate_on_screen`), a cada
execução — nunca depende de `window.geometry()` pra calcular posição, só
pra saber quando o cache expirou (a janela pode ter mudado de lugar,
tamanho ou MODO; não dá pra saber qual sem medir de novo). Com a fração
conhecida de cada âncora e o pixel real onde foi achada, o sistema
escala+translação por eixo se resolve exato com 2 pontos — o mínimo
matemático quando só escala e posição podem variar (sem rotação nem
cisalhamento; ver ROADMAP.md sobre quando isso deixa de bastar).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Tuple

from prumo.core.exceptions import LocatorError
from prumo.core.locator import PointLocator


@dataclass(frozen=True)
class Anchor:
    """Uma âncora: a fração conhecida do ponto + o caminho do template que
    o driver usa pra achá-lo na tela real."""

    locator: PointLocator
    template_path: str


class AnchorZone:
    """Resolve locators (fração 0.0-1.0) pra pixel absoluto de tela usando
    2 âncoras localizadas por imagem, em vez de fração fixa de
    `window.geometry()`.

    O resultado (a transformação linear por eixo) é cacheado até
    `geometry_key()` mudar de valor — evita refazer a busca de imagem
    (custa dezenas a centenas de ms) a cada resolução.
    """

    def __init__(
        self,
        anchor1: Anchor,
        anchor2: Anchor,
        *,
        locate: Callable[[str], Optional[Tuple[float, float]]],
        geometry_key: Callable[[], object],
    ):
        self._anchor1 = anchor1
        self._anchor2 = anchor2
        self._locate = locate
        self._geometry_key = geometry_key
        self._cache: Optional[Tuple[float, float, float, float]] = None
        self._cache_key: object = None

    def _locate_or_raise(self, anchor: Anchor) -> Tuple[float, float]:
        found = self._locate(anchor.template_path)
        if found is None:
            raise LocatorError(
                f"âncora não encontrada na tela (template '{anchor.template_path}') — "
                f"a aplicação pode não estar visível, ou o tema/layout mudou o "
                f"suficiente pra invalidar o template"
            )
        return found

    def _transform(self) -> Tuple[float, float, float, float]:
        """(Ax, Bx, Ay, By) tal que pixel = A*fração + B, por eixo."""
        key = self._geometry_key()
        if key != self._cache_key:
            self._cache = None
            self._cache_key = key

        if self._cache is None:
            p1x, p1y = self._locate_or_raise(self._anchor1)
            p2x, p2y = self._locate_or_raise(self._anchor2)
            l1, l2 = self._anchor1.locator, self._anchor2.locator
            if l1.x == l2.x or l1.y == l2.y:
                raise LocatorError(
                    "as duas âncoras de uma AnchorZone precisam ter x E y "
                    "diferentes entre si (cantos opostos) — frações iguais "
                    "não resolvem o sistema escala+translação"
                )
            ax = (p2x - p1x) / (l2.x - l1.x)
            bx = p1x - ax * l1.x
            ay = (p2y - p1y) / (l2.y - l1.y)
            by = p1y - ay * l1.y
            self._cache = (ax, bx, ay, by)
        return self._cache

    def resolve(self, locator: PointLocator) -> Tuple[int, int]:
        ax, bx, ay, by = self._transform()
        return round(ax * locator.x + bx), round(ay * locator.y + by)
