"""Ritmo humano para o driver real — ARCHITECTURE.md §9.9.

Achado real (hp-prime-automation, 22/09/2026): a mesma sequência que
funcionava com clique manual pausado falhava rodando em cadência de
máquina — clique "teletransportado" sem trajeto, tecla pressionada e solta
no mesmo instante, próxima ação disparada antes de o app (pesado: a HP
Prime Virtual Calculator emula o hardware inteiro) terminar de processar a
anterior. Um usuário humano leva centenas de milissegundos entre ações, move
o mouse ao longo de um trajeto e segura a tecla por um instante. Estes
valores reproduzem isso — o objetivo não é "parecer humano" pra enganar
ninguém, é dar ao app o mesmo tempo que ele teria com uma pessoa operando.

Nada aqui substitui esperar o ESTADO certo na tela (`GUIAutomator.
wait_for_template`, §9.6): o ritmo humano é o piso de tempo entre ações;
a confirmação de estado é o que autoriza a próxima.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class HumanPacing:
    # trajeto do mouse: duração proporcional à distância, com piso e teto
    move_px_per_s: float = 900.0
    move_min_s: float = 0.18
    move_max_s: float = 0.65
    # pausa entre chegar no alvo e apertar (mira)
    pre_click_s: float = 0.12
    # tempo com o botão/tecla pressionado antes de soltar
    hold_s: float = 0.09
    # pausa depois de soltar, antes da próxima ação
    post_action_s: float = 0.35
    # intervalo entre caracteres digitados
    char_delay_s: float = 0.11
    # quanto tempo esperar o SO confirmar que o botão/tecla foi solto
    release_timeout_s: float = 1.0
    # variação aleatória (+/- fração) aplicada às pausas
    jitter: float = 0.15

    def varia(self, base: float) -> float:
        if self.jitter <= 0:
            return base
        return max(0.0, base * (1 + random.uniform(-self.jitter, self.jitter)))

    def move_duration(self, dist_px: float) -> float:
        bruto = dist_px / self.move_px_per_s if self.move_px_per_s > 0 else self.move_min_s
        return self.varia(min(self.move_max_s, max(self.move_min_s, bruto)))


def distancia(a, b) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])
