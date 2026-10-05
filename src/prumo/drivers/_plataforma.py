"""Proteções que só existem no Windows — e o aviso de quando estão desligadas.

Os gates do `prumo` (oclusão, primeiro plano, soltura confirmada) perguntam ao
Win32. Fora do Windows não há a quem perguntar, e eles deixam passar. Isso é
uma escolha (não quebrar quem roda noutro SO), mas não pode ser silenciosa: a
primeira vez que cada gate é pulado, sai um aviso no log dizendo qual proteção
está desligada (ARCHITECTURE.md §9.12).
"""

from __future__ import annotations

import logging
import sys
from typing import Set

logger = logging.getLogger("prumo")

_avisados: Set[str] = set()


def avisar_uma_vez(chave: str, mensagem: str) -> None:
    """Aviso no log na primeira vez que `chave` aparece; depois, silêncio —
    um gate desligado avisa uma vez, não a cada clique."""
    if chave not in _avisados:
        _avisados.add(chave)
        logger.warning("%s", mensagem)


def sem_win32(protecao: str) -> bool:
    """`True` se não há Win32 para consultar (e `protecao` está desligada).
    Avisa no log uma vez por `protecao`."""
    if sys.platform == "win32":
        return False
    avisar_uma_vez(protecao, f"{protecao} DESLIGADA: fora do Windows não há como checar (sys.platform={sys.platform})")
    return True
