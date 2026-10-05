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
import time
from typing import Optional, Tuple

from prumo.core.exceptions import InputReleaseError
from prumo.drivers.base import InputDriver
from prumo.drivers.pacing import HumanPacing, distancia
from prumo.drivers.release import confirm_released


# nome do botão no pyautogui -> nome em `release.VIRTUAL_KEYS`; o que não
# estiver aqui ("left", "primary"...) é o esquerdo, como sempre foi
_BOTAO = {"right": "mouse_right", "secondary": "mouse_right", "middle": "mouse_middle"}


class PyAutoGuiDriver(InputDriver):
    """`pacing` (padrão: `HumanPacing()`) liga o ritmo humano — trajeto do
    mouse, mira, tecla segurada por um instante, confirmação de soltura no
    SO e pausa depois de cada ação (ARCHITECTURE.md §9.9). `pacing=None`
    volta ao comportamento cru antigo (clique instantâneo), só pra quem
    sabe que o app aguenta."""

    def __init__(self, *, pause: float = 0.1, failsafe: bool = True, pacing: Optional[HumanPacing] = HumanPacing()):
        self._ensure_dpi_awareness()

        import pyautogui

        pyautogui.FAILSAFE = failsafe
        pyautogui.PAUSE = 0.0 if pacing is not None else pause
        self._pyautogui = pyautogui
        self.pacing = pacing

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
        p = self.pacing
        if p is None:
            self._pyautogui.click(x=x, y=y, button=button, clicks=clicks)
            return
        self.move_to(x, y)
        time.sleep(p.varia(p.pre_click_s))
        for i in range(clicks):
            self._pyautogui.mouseDown(x=x, y=y, button=button)
            time.sleep(p.varia(p.hold_s))
            self._pyautogui.mouseUp(x=x, y=y, button=button)
            self._confirmar_soltura_mouse(button)
            if i < clicks - 1:
                time.sleep(p.varia(p.hold_s))
        time.sleep(p.varia(p.post_action_s))

    def _confirmar_soltura_mouse(self, button: str) -> None:
        """Só devolve quando o SO diz que o botão está solto — nunca segue
        com botão pressionado (ARCHITECTURE.md §9.9)."""
        try:
            confirm_released((_BOTAO.get(button, "mouse_left"),), timeout=self.pacing.release_timeout_s)
        except InputReleaseError as exc:
            raise InputReleaseError(f"botão '{button}' do mouse continua pressionado após o clique") from exc

    def move_to(self, x: int, y: int, *, duration: float = 0.0) -> None:
        """`duration=0` pula direto (rápido, o caso comum). Alguns popups
        (achado real: menu Qt nativo da HP Prime) só rastreiam o item sob o
        cursor com movimento incremental de verdade — um salto instantâneo
        não gera hover, e o clique subsequente não executa o comando mesmo
        fechando o popup normalmente. `duration > 0` resolve isso."""
        if duration <= 0 and self.pacing is not None:
            atual = tuple(self._pyautogui.position())
            duration = self.pacing.move_duration(distancia(atual, (x, y)))
        self._pyautogui.moveTo(x, y, duration=duration, tween=self._pyautogui.easeInOutQuad)

    def press(self, key: str) -> None:
        if self.pacing is None:
            self._keyboard.send(key)
            return
        self._segura_e_solta([key])

    def hotkey(self, *keys: str) -> None:
        if self.pacing is None:
            self._keyboard.send("+".join(keys))
            return
        self._segura_e_solta(list(keys))

    def _segura_e_solta(self, keys) -> None:
        """Pressiona na ordem, segura um instante, solta na ordem inversa e
        CONFIRMA que cada uma foi solta antes de devolver."""
        p = self.pacing
        for k in keys:
            self._keyboard.press(k)
            time.sleep(p.varia(p.hold_s) / 2)
        time.sleep(p.varia(p.hold_s))
        for k in reversed(keys):
            self._keyboard.release(k)
        prazo = time.monotonic() + p.release_timeout_s
        while any(self._keyboard.is_pressed(k) for k in keys):
            if time.monotonic() > prazo:
                raise InputReleaseError(f"tecla(s) {keys} continuam pressionadas após soltar")
            time.sleep(0.02)
        time.sleep(p.varia(p.post_action_s))

    def write(self, text: str, *, delay: float = 0.0) -> None:
        """`delay=0` escreve tudo de uma vez (rápido, o caso comum).
        Algumas aplicações (achado real: diálogo "Novo programa" da HP
        Prime) derrubam caractere quando `keyboard.write()` digita rápido
        demais — `"TESTEXX"` chegou como `"TEXX"`. `delay > 0` escreve um
        caractere de cada vez, com pausa entre eles."""
        if delay <= 0 and self.pacing is not None:
            delay = self.pacing.char_delay_s
        if delay <= 0:
            self._keyboard.write(text)
            return
        for ch in text:
            self._keyboard.write(ch)
            time.sleep(delay)

    def drag(self, start: Tuple[int, int], end: Tuple[int, int], *, duration: float = 0.5) -> None:
        self._pyautogui.moveTo(*start)
        self._pyautogui.dragTo(*end, duration=duration, button="left")
        # Mesma regra do `click` (§9.9): nunca segue com o botão pressionado. O `drag` era o único gesto de mouse
        # sem a confirmação — achado ao usá-lo no e2e do painel-nativo (01/10/2026), onde soltar é o que dispara o comando.
        if self.pacing is not None:
            self._confirmar_soltura_mouse("left")
            time.sleep(self.pacing.varia(self.pacing.post_action_s))

    def screenshot(self, region: Optional[Tuple[int, int, int, int]] = None):
        return self._pyautogui.screenshot(region=region)

    def screen_size(self) -> Tuple[int, int]:
        return tuple(self._pyautogui.size())

    def locate_on_screen(
        self, template_path: str, *, confidence: float = 0.85
    ) -> Optional[Tuple[float, float]]:
        """Casamento no tamanho exato primeiro (rápido, é o caso comum);
        se falhar, tenta múltiplas escalas do template antes de desistir
        — a mesma aplicação pode renderizar o mesmo botão em tamanhos
        diferentes entre modos de layout (não é só reposicionamento; ver
        `_template_match.py`)."""
        try:
            box = self._pyautogui.locateOnScreen(template_path, confidence=confidence)
        except self._pyautogui.ImageNotFoundException:
            box = None
        if box is not None:
            x, y = self._pyautogui.center(box)
            return float(x), float(y)

        return self._locate_multi_scale(template_path, confidence=confidence)

    def _locate_multi_scale(
        self, template_path: str, *, confidence: float
    ) -> Optional[Tuple[float, float]]:
        import cv2
        import numpy as np

        from prumo.drivers._template_match import locate_multi_scale

        template = cv2.imread(template_path)
        if template is None:
            return None
        screenshot = self._pyautogui.screenshot()
        screen = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        return locate_multi_scale(screen, template, confidence=confidence)

    def read_clipboard(self) -> str:
        """Lê como CF_UNICODETEXT — CF_TEXT (ANSI) perde glifos fora do cp1252
        (achado real: HP Prime usa U+1D07 pra notação científica, não "e" ASCII)."""
        import win32clipboard

        win32clipboard.OpenClipboard()
        try:
            return win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
        finally:
            win32clipboard.CloseClipboard()

    def write_clipboard(self, text: str) -> None:
        import win32clipboard

        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
        finally:
            win32clipboard.CloseClipboard()

    def cursor_position(self) -> Tuple[int, int]:
        # mesmo sistema de coordenadas do clique: o DPI awareness foi ligado
        # no construtor, antes de qualquer leitura (§9.9)
        x, y = self._pyautogui.position()
        return (int(x), int(y))

    def is_key_down(self, key: str) -> bool:
        return bool(self._keyboard.is_pressed(key))
