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

import logging
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

from prumo.core.exceptions import InputReleaseError, LocatorError
from prumo.drivers.base import InputDriver
from prumo.drivers.pacing import HumanPacing, distancia
from prumo.drivers.release import confirm_released

logger = logging.getLogger("prumo")


# nome do botão no pyautogui -> nome em `release.VIRTUAL_KEYS`; o que não
# estiver aqui ("left", "primary"...) é o esquerdo, como sempre foi
_BOTAO = {"right": "mouse_right", "secondary": "mouse_right", "middle": "mouse_middle"}


class PyAutoGuiDriver(InputDriver):
    """`pacing` (padrão: `HumanPacing()`) liga o ritmo humano — trajeto do
    mouse, mira, tecla segurada por um instante, confirmação de soltura no
    SO e pausa depois de cada ação (ARCHITECTURE.md §9.9). `pacing=None`
    volta ao comportamento cru antigo (clique instantâneo), só pra quem
    sabe que o app aguenta."""

    # HumanPacing é frozen: a instância padrão compartilhada é imutável, não vaza estado entre drivers
    def __init__(self, *, pause: float = 0.1, failsafe: bool = True, pacing: Optional[HumanPacing] = HumanPacing()):  # noqa: B008
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
        """Liga o DPI awareness do processo ANTES de qualquer leitura de
        coordenada. Sem ele, em tela com escala ≠ 100%, o pixel que o mouse
        recebe, o retângulo da UIA e o do `WindowManager` divergem — e o
        clique cai fora do lugar sem erro nenhum (achado do e2e da Tina, §9.9).

        As duas chamadas podem falhar por motivos inofensivos (Windows antigo
        sem `shcore`; awareness já definido por outro caminho). Por isso o que
        decide é a conferência no fim: se o processo NÃO ficou DPI-aware, isso
        vai pro log como aviso, em vez de sumir."""
        if sys.platform != "win32":
            return
        import ctypes

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        except Exception:  # noqa: BLE001 - sem shcore (Windows antigo): tenta a API anterior
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception as exc:  # noqa: BLE001 - quem decide é a conferência abaixo
                logger.debug("SetProcessDPIAware levantou: %s", exc)
        if not ctypes.windll.user32.IsProcessDPIAware():
            logger.warning(
                "o processo NÃO está DPI-aware: em tela com escala diferente de 100%%, "
                "coordenadas do mouse, da UIA e da janela divergem e o clique pode cair "
                "fora do lugar (ARCHITECTURE.md §9.9)"
            )

    def click(self, x: int, y: int, *, button: str = "left", clicks: int = 1) -> None:
        p = self.pacing
        if p is None:
            self._pyautogui.click(x=x, y=y, button=button, clicks=clicks)
            return
        self.move_to(x, y)
        time.sleep(p.varia(p.pre_click_s))
        for i in range(clicks):
            self._pyautogui.mouseDown(x=x, y=y, button=button)
            try:
                time.sleep(p.varia(p.hold_s))
                self._pyautogui.mouseUp(x=x, y=y, button=button)
            except BaseException:
                # Ctrl+C ou FAILSAFE no instante segurado: o botão NÃO pode
                # ficar preso no SO — solta e deixa a interrupção seguir
                self._soltar_botao_sem_mover(button)
                raise
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

    def _soltar_botao_sem_mover(self, button: str) -> None:
        """Soltura de emergência, depois de uma interrupção com o botão
        apertado. Duas regras: (1) solta ONDE o mouse estiver — não se move o
        mouse de quem pode ter acabado de assumir; (2) o FAILSAFE fica
        desligado só nesta chamada — com o mouse no canto ele levantaria
        exceção antes de soltar, impedindo justamente a soltura."""
        anterior = self._pyautogui.FAILSAFE
        self._pyautogui.FAILSAFE = False
        try:
            self._pyautogui.mouseUp(button=button)
        finally:
            self._pyautogui.FAILSAFE = anterior

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
        apertadas = []
        try:
            for k in keys:
                self._keyboard.press(k)
                apertadas.append(k)
                time.sleep(p.varia(p.hold_s) / 2)
            time.sleep(p.varia(p.hold_s))
        finally:
            # solta o que foi apertado mesmo se algo interromper no meio
            # (Ctrl+C): um Shift preso vale pra máquina inteira, não só pro app
            for k in reversed(apertadas):
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
        try:
            self._pyautogui.dragTo(*end, duration=duration, button="left")
        except BaseException:
            # o dragTo aperta, move e solta; interrompido no meio (FAILSAFE no
            # trajeto, Ctrl+C), ele sai com o botão apertado
            self._soltar_botao_sem_mover("left")
            raise
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
        template = self._carregar_template(template_path)
        try:
            box = self._pyautogui.locateOnScreen(template, confidence=confidence)
        except self._pyautogui.ImageNotFoundException:
            box = None
        if box is not None:
            x, y = self._pyautogui.center(box)
            return float(x), float(y)

        return self._locate_multi_scale(template, confidence=confidence)

    @staticmethod
    def _carregar_template(template_path: str):
        """Lê o recorte UMA vez, como matriz BGR do OpenCV (o que as duas
        buscas aceitam). O `cv2.imread` devolve `None` em silêncio para
        caminho com acento no Windows (`Conteúdo`, `matérias`...); lido por
        bytes (`np.fromfile` + `cv2.imdecode`), o acento deixa de importar.
        Arquivo ausente ou que não é imagem vira erro claro AQUI — e não
        "não achei na tela" depois de esgotar o timeout inteiro."""
        import cv2
        import numpy as np

        caminho = Path(template_path)
        if not caminho.is_file():
            raise FileNotFoundError(f"template não existe: {template_path}")
        imagem = cv2.imdecode(np.fromfile(str(caminho), dtype=np.uint8), cv2.IMREAD_COLOR)
        if imagem is None:
            raise LocatorError(f"template ilegível (o OpenCV não decodifica como imagem): {template_path}")
        return imagem

    def _locate_multi_scale(self, template, *, confidence: float) -> Optional[Tuple[float, float]]:
        import cv2
        import numpy as np

        from prumo.drivers._template_match import locate_multi_scale

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
