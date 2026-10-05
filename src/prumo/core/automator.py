"""GUIAutomator — ARCHITECTURE.md §4, §16.

Orquestra WindowManager, driver, locators, estado, interrupções e
recuperação. Aplicações específicas (ex.: HpPrimeCalculator, em
hp-prime-automation) herdam desta classe e só adicionam o que conhecem da
própria aplicação — nunca chamam o driver diretamente (§1.2). Este módulo
não sabe que HP Prime existe.
"""

from __future__ import annotations

import itertools
import logging
import time
from contextlib import contextmanager
from typing import Callable, Dict, Iterator, Mapping, Optional, Tuple

from prumo.core.events import InterruptionManager
from prumo.core.exceptions import AutomationTimeoutError, LocatorError, WindowOccludedError
from prumo.core.guard import TakeoverGuard
from prumo.core.locator import Locator, RegionLocator
from prumo.core.recovery import RecoveryManager
from prumo.core.state import GUIState, StateManager
from prumo.core.transaction import transaction as _transaction
from prumo.drivers.base import InputDriver
from prumo.drivers.window import WindowManager

logger = logging.getLogger("prumo")


class GUIAutomator:
    def __init__(
        self,
        *,
        window: WindowManager,
        driver: InputDriver,
        locators: Mapping[str, Locator],
        state_detector: Callable[[], GUIState],
        interruptions: Optional[InterruptionManager] = None,
        recovery: Optional[RecoveryManager] = None,
        guard: Optional[TakeoverGuard] = None,
    ):
        """`guard` (opt-in) liga a trava de "o usuário assumiu" em toda ação
        (ARCHITECTURE.md §9.12): checa antes, marca onde deixou o mouse
        depois."""
        self.window = window
        self.driver = driver
        self.locators: Dict[str, Locator] = dict(locators)
        self.state = StateManager(state_detector)
        self.interruptions = interruptions or InterruptionManager()
        self.recovery = recovery or RecoveryManager()
        self.guard = guard
        self._op_ids = itertools.count(1)

    # --- locators -----------------------------------------------------

    def locator(self, name: str) -> Locator:
        try:
            return self.locators[name]
        except KeyError as exc:
            raise LocatorError(f"locator '{name}' não existe no mapa carregado") from exc

    def resolve(self, name: str):
        loc = self.locator(name)
        geometry = self.window.geometry()
        if isinstance(loc, RegionLocator):
            loc = loc.center
        return geometry.to_absolute(loc.x, loc.y)

    # --- pré-condição / interrupções (ARCHITECTURE.md §12.1) -----------

    def precheck(self, what: str = "") -> None:
        # a trava vem ANTES do activate(): quem acabou de assumir o mouse não
        # pode ter o foco roubado de volta (§9.12)
        if self.guard is not None:
            self.guard.check(what)
        if not self.window.is_alive():
            self.window.find()
        self.window.activate()
        self.interruptions.check_and_handle()

    def ensure_ready(self, timeout: float = 5.0) -> GUIState:
        self.precheck()
        try:
            return self.state.wait_for(GUIState.READY, timeout=timeout)
        except AutomationTimeoutError:
            if not self.recovery.steps:
                raise
            return self.recovery.recover(self, timeout=timeout)

    # --- ações (cada uma loga com um operation id, ARCHITECTURE.md §18) -

    def _next_op(self) -> int:
        return next(self._op_ids)

    def _mark(self) -> None:
        if self.guard is not None:
            self.guard.mark()

    def click(self, locator_name: str) -> None:
        op = self._next_op()
        self.precheck(f"click {locator_name}")
        x, y = self.resolve(locator_name)
        logger.info("op=%s action=click(%s) absoluto=(%s, %s)", op, locator_name, x, y)
        self.click_at(x, y, rotulo=locator_name)

    def click_at(self, x: int, y: int, *, rotulo: str = "") -> None:
        """Clique em coordenada absoluta, MAS só se o ponto pertence à
        janela-alvo (`WindowManager.owns_point`) — levanta
        `WindowOccludedError` em vez de clicar numa janela por cima
        (ARCHITECTURE.md §9.9). Use isto, não `driver.click`, pra qualquer
        clique fora do mapa de locators (softkey, menu, chrome nativo)."""
        if self.guard is not None:
            self.guard.check(f"click_at ({x}, {y}) {rotulo}".rstrip())
        self._garantir_ponto(x, y, rotulo)
        self.driver.click(x, y)
        self._mark()

    def _garantir_ponto(self, x: int, y: int, rotulo: str) -> None:
        owns = getattr(self.window, "owns_point", None)
        if owns is not None and not owns(x, y):
            raise WindowOccludedError(
                f"ponto ({x}, {y}) [{rotulo}] está coberto por outra janela — "
                f"a janela-alvo tem foco mas não está visível ali. Tire a janela "
                f"de cima (ou mova a janela-alvo) antes de continuar."
            )

    def move_to(self, x: int, y: int, *, duration: float = 0.0, rotulo: str = "") -> None:
        """Move o mouse sem clicar (hover — ex.: o popup de menu do Qt só
        reconhece o item sob o cursor com movimento de verdade, §9.4). Passa
        pela trava (§9.12): use isto, não `driver.move_to` — com a trava
        ligada, um movimento direto no driver parece, no gesto seguinte, a
        mão do usuário. Não confere oclusão: mover não aciona nada."""
        if self.guard is not None:
            self.guard.check(f"move_to ({x}, {y}) {rotulo}".rstrip())
        self.driver.move_to(x, y, duration=duration)
        self._mark()

    def drag(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        *,
        duration: float = 0.5,
        rotulo: str = "",
        occlusion_gate: bool = True,
    ) -> None:
        """Arrasto com o gate de oclusão nas DUAS pontas — soltar fora da
        janela-alvo dispararia o gesto noutro app — e com a trava (§9.12).
        Use isto, não `driver.drag`.

        `occlusion_gate=False` é para quando o alvo É outro app, de propósito
        (ex.: a sobreposição de recorte do Windows depois do PrtScn). A trava
        continua valendo: o que se desliga é só a exigência de que as pontas
        sejam da janela-alvo."""
        op = self._next_op()
        if self.guard is not None:
            self.guard.check(f"drag {rotulo}".rstrip())
        if occlusion_gate:
            self._garantir_ponto(start[0], start[1], f"{rotulo} (início)".strip())
            self._garantir_ponto(end[0], end[1], f"{rotulo} (fim)".strip())
        else:
            logger.info("op=%s drag sem gate de oclusão (alvo fora da janela, declarado): %s", op, rotulo)
        logger.info("op=%s action=drag(%s -> %s, duration=%s)", op, start, end, duration)
        self.driver.drag(start, end, duration=duration)
        self._mark()

    def press(self, key: str) -> None:
        op = self._next_op()
        self.precheck(f"press {key}")
        logger.info("op=%s action=press(%s)", op, key)
        self.driver.press(key)
        self._mark()

    def hotkey(self, *keys: str) -> None:
        op = self._next_op()
        self.precheck(f"hotkey {'+'.join(keys)}")
        logger.info("op=%s action=hotkey(%s)", op, "+".join(keys))
        self.driver.hotkey(*keys)
        self._mark()

    def write(self, text: str, *, delay: float = 0.0) -> None:
        op = self._next_op()
        self.precheck("write")
        logger.info("op=%s action=write(%r, delay=%s)", op, text, delay)
        self.driver.write(text, delay=delay)
        self._mark()

    # --- leitura de pixel (decisões simples: indicador verde/vermelho...) -

    def color_at(self, locator_name: str) -> Tuple[int, int, int]:
        """Cor (r, g, b) do pixel em `locator_name`. Usa `self.resolve()` —
        uma subclasse que resolve locators de outro jeito (ex.: por âncora
        de imagem, ver `core.anchors.AnchorZone`) herda isso de graça."""
        self.precheck()
        x, y = self.resolve(locator_name)
        pixel = self.driver.screenshot(region=(x, y, 1, 1))
        r, g, b = pixel.getpixel((0, 0))[:3]
        return (r, g, b)

    def color_matches(
        self, locator_name: str, expected: Tuple[int, int, int], *, tolerance: int = 10
    ) -> bool:
        r, g, b = self.color_at(locator_name)
        er, eg, eb = expected
        return abs(r - er) <= tolerance and abs(g - eg) <= tolerance and abs(b - eb) <= tolerance

    def wait_for_color_change(
        self,
        color_at: Callable[[], Tuple[int, int, int]],
        *,
        from_color: Tuple[int, int, int],
        timeout: float,
        poll_interval: float = 0.5,
        tolerance: int = 10,
    ) -> Tuple[int, int, int]:
        """Espera até `color_at()` deixar de bater com `from_color` e devolve
        a cor nova. Levanta `AutomationTimeoutError` se `timeout` esgotar
        primeiro — nunca segue em frente sem saber se algo mudou de verdade.

        `color_at` é qualquer callable sem argumento que devolve (r, g, b) —
        mesma forma de `core.state.color_based_detector`, não precisa ser
        `self.color_at(locator_name)` (útil quando o pixel de interesse não
        é um locator do mapa, ex.: chrome nativo do app fora do teclado
        virtual).

        Nasceu de um achado real: o popup de "Verif." da HP Prime pode levar
        minutos pra aparecer num programa grande (CPU do processo perto de
        100% o tempo todo — ocupado de verdade, não travado), e um sleep
        fixo curto clica no botão de fechar antes do popup existir, o que
        na prática clica de novo no botão que ABRE a operação — reinicia em
        vez de fechar o resultado."""
        deadline = time.monotonic() + timeout
        color = color_at()
        while all(abs(a - b) <= tolerance for a, b in zip(color, from_color, strict=True)):
            if time.monotonic() > deadline:
                raise AutomationTimeoutError(
                    f"timeout de {timeout}s esperando a cor mudar de {from_color}"
                )
            time.sleep(poll_interval)
            color = color_at()
        return color

    def wait_for_template(
        self,
        template_path: str,
        *,
        timeout: float = 15.0,
        poll_interval: float = 0.25,
        confidence: float = 0.9,
    ) -> Tuple[float, float]:
        """Espera o template (recorte PNG de um estado da tela) aparecer e
        devolve o centro onde foi achado. Levanta `AutomationTimeoutError`
        se `timeout` esgotar — nunca segue sem ter VISTO o estado esperado.

        É o gate entre etapas (ARCHITECTURE.md §9.9): ação → espera o estado
        que ela deveria produzir → só então a próxima ação. Timeout padrão
        generoso de propósito: app pesado (emulador, software de engenharia)
        pode levar segundos pra redesenhar — errar pelo lado da paciência
        custa segundos; errar pelo lado da pressa corrompe a sessão."""
        deadline = time.monotonic() + timeout
        while True:
            pos = self.driver.locate_on_screen(template_path, confidence=confidence)
            if pos is not None:
                return pos
            if time.monotonic() > deadline:
                raise AutomationTimeoutError(
                    f"timeout de {timeout}s esperando aparecer na tela: {template_path}"
                )
            time.sleep(poll_interval)

    def wait_for_template_gone(
        self,
        template_path: str,
        *,
        timeout: float = 15.0,
        poll_interval: float = 0.25,
        confidence: float = 0.9,
    ) -> None:
        """Espera o template SUMIR da tela (ex.: diálogo fechou, indicador
        de modificador apagou). Levanta `AutomationTimeoutError` se continuar
        lá depois de `timeout`."""
        deadline = time.monotonic() + timeout
        while self.driver.locate_on_screen(template_path, confidence=confidence) is not None:
            if time.monotonic() > deadline:
                raise AutomationTimeoutError(
                    f"timeout de {timeout}s esperando sumir da tela: {template_path}"
                )
            time.sleep(poll_interval)

    def is_on_screen(self, template_path: str, *, confidence: float = 0.9) -> bool:
        """Sonda única, sem esperar — pra checar AUSÊNCIA de algo que não
        deveria estar lá (ex.: popup de erro) logo depois de uma espera."""
        return self.driver.locate_on_screen(template_path, confidence=confidence) is not None

    # --- transação --------------------------------------------------------

    @contextmanager
    def transaction(self, *, timeout: float = 5.0) -> Iterator["GUIAutomator"]:
        with _transaction(self, timeout=timeout) as automator:
            yield automator
