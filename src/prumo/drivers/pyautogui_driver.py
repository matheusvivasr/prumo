"""Driver real via PyAutoGUI + `keyboard` — ARCHITECTURE.md §9.

Divisão: pyautogui cuida do mouse e da leitura de tela; `keyboard` cuida do
teclado (lida melhor com Unicode/acentos do que pyautogui.typewrite). Ativa
DPI awareness no Windows antes do primeiro uso — sem isso, telas com escala
!= 100% fazem clique e coordenada não baterem (mesmo problema resolvido em
hp-prime-automation/core/dpi_awareness.py).

`locate_on_screen` usa `confidence=`, que exige `opencv-python` instalado
(dependência opcional do pyautogui — não é hard dependency do prumo, quem
usa âncoras por imagem instala por conta).
"""

from __future__ import annotations

import sys
from typing import Optional, Tuple

from prumo.drivers.base import InputDriver


class PyAutoGuiDriver(InputDriver):
    def __init__(self, *, pause: float = 0.1, failsafe: bool = True):
        self._ensure_dpi_awareness()

        import pyautogui

        pyautogui.FAILSAFE = failsafe
        pyautogui.PAUSE = pause
        self._pyautogui = pyautogui

        import keyboard

        self._keyboard = keyboard

    @staticmethod
    def _ensure_dpi_awareness() -> None:
        if sys.platform != "win32":
            return
        import ctypes

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

    def click(self, x: int, y: int, *, button: str = "left", clicks: int = 1) -> None:
        self._pyautogui.click(x=x, y=y, button=button, clicks=clicks)

    def move_to(self, x: int, y: int) -> None:
        self._pyautogui.moveTo(x, y)

    def press(self, key: str) -> None:
        self._keyboard.send(key)

    def hotkey(self, *keys: str) -> None:
        self._keyboard.send("+".join(keys))

    def write(self, text: str) -> None:
        self._keyboard.write(text)

    def drag(self, start: Tuple[int, int], end: Tuple[int, int], *, duration: float = 0.5) -> None:
        self._pyautogui.moveTo(*start)
        self._pyautogui.dragTo(*end, duration=duration, button="left")

    def screenshot(self, region: Optional[Tuple[int, int, int, int]] = None):
        return self._pyautogui.screenshot(region=region)

    def screen_size(self) -> Tuple[int, int]:
        return tuple(self._pyautogui.size())

    def locate_on_screen(
        self, template_path: str, *, confidence: float = 0.85
    ) -> Optional[Tuple[float, float]]:
        try:
            box = self._pyautogui.locateOnScreen(template_path, confidence=confidence)
        except self._pyautogui.ImageNotFoundException:
            return None
        if box is None:
            return None
        x, y = self._pyautogui.center(box)
        return float(x), float(y)
