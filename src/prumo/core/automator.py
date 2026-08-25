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
from contextlib import contextmanager
from typing import Callable, Dict, Iterator, Mapping, Optional, Tuple

from prumo.core.events import InterruptionManager
from prumo.core.exceptions import AutomationTimeoutError, LocatorError
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
    ):
        self.window = window
        self.driver = driver
        self.locators: Dict[str, Locator] = dict(locators)
        self.state = StateManager(state_detector)
        self.interruptions = interruptions or InterruptionManager()
        self.recovery = recovery or RecoveryManager()
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

    def precheck(self) -> None:
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

    def click(self, locator_name: str) -> None:
        op = self._next_op()
        self.precheck()
        x, y = self.resolve(locator_name)
        logger.info("op=%s action=click(%s) absoluto=(%s, %s)", op, locator_name, x, y)
        self.driver.click(x, y)

    def press(self, key: str) -> None:
        op = self._next_op()
        self.precheck()
        logger.info("op=%s action=press(%s)", op, key)
        self.driver.press(key)

    def hotkey(self, *keys: str) -> None:
        op = self._next_op()
        self.precheck()
        logger.info("op=%s action=hotkey(%s)", op, "+".join(keys))
        self.driver.hotkey(*keys)

    def write(self, text: str) -> None:
        op = self._next_op()
        self.precheck()
        logger.info("op=%s action=write(%r)", op, text)
        self.driver.write(text)

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

    # --- transação --------------------------------------------------------

    @contextmanager
    def transaction(self, *, timeout: float = 5.0) -> Iterator["GUIAutomator"]:
        with _transaction(self, timeout=timeout) as automator:
            yield automator
