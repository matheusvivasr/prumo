"""WindowManager — ARCHITECTURE.md §8.

Responsável exclusivamente pela janela: localizar, ativar, medir,
verificar se ainda existe. A origem usada para coordenadas relativas é
(left, top) da janela, incluindo o header — mesmo critério já validado em
hp-prime-automation/core/janela_utils.py (a origem histórica do projeto).
"""

from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass
from typing import Tuple

from prumo.core.exceptions import WindowActivationError, WindowNotFoundError, WindowOccludedError

logger = logging.getLogger("prumo")

# ALT (VK_MENU) — usado só pra "soltar" o foreground lock do Windows, nunca
# chega a nenhum campo de texto (keyup imediato depois do keydown).
_VK_MENU = 0x12
_KEYEVENTF_KEYUP = 0x0002


@dataclass(frozen=True)
class WindowGeometry:
    left: int
    top: int
    width: int
    height: int

    def to_absolute(self, rel_x: float, rel_y: float) -> Tuple[int, int]:
        """Converte coordenada relativa à janela (0.0-1.0) em pixel de tela."""
        return (
            self.left + round(rel_x * self.width),
            self.top + round(rel_y * self.height),
        )


class WindowManager:
    def __init__(
        self,
        title: str,
        *,
        exact: bool = False,
        attempts: int = 5,
        retry_interval: float = 0.5,
    ):
        self.title = title
        self.exact = exact
        self.attempts = attempts
        self.retry_interval = retry_interval
        self._window = None

    def find(self):
        import pygetwindow as gw

        for _ in range(self.attempts):
            candidates = [
                w
                for w in gw.getAllWindows()
                if w.title.strip()
                and (w.title == self.title if self.exact else self.title.lower() in w.title.lower())
            ]
            if candidates:
                self._window = candidates[0]
                return self._window
            time.sleep(self.retry_interval)

        raise WindowNotFoundError(
            f"nenhuma janela encontrada para título '{self.title}' "
            f"(exact={self.exact}) após {self.attempts} tentativa(s)"
        )

    def activate(self) -> None:
        """Traz a janela pro primeiro plano — e **confirma** que conseguiu,
        não só que a chamada não levantou exceção.

        Achado real (hp-prime-automation, 01/09/2026): `pygetwindow.activate()`
        chama `SetForegroundWindow` do Windows, que pode ser **recusado
        silenciosamente** (sem exceção nenhuma) quando outro processo já tem
        o foco — o chamado "foreground lock" do Windows, uma proteção contra
        janela roubando foco do usuário à toa. O sintoma: a janela nunca vem
        pra frente, e qualquer automação baseada em screenshot
        (`locate_on_screen`) falha achando que a âncora "não está na tela" —
        quando na verdade a tela mostra outra janela por cima.

        Contorno documentado pela própria Microsoft: simular uma tecla solta
        (aqui, ALT — nunca chega a nenhum campo de texto, é keydown+keyup
        imediato) libera o processo atual pra chamar `SetForegroundWindow`
        de novo com sucesso. Depois do contorno, verifica de novo via
        `window.isActive` (não confia que "não deu erro" = "funcionou") e
        levanta `WindowActivationError` se mesmo assim não conseguiu — é
        melhor falhar alto aqui do que deixar quem chamou (uma macro) clicar
        às cegas numa janela que não está realmente em primeiro plano.
        """
        window = self._window or self.find()
        if window.isMinimized:
            window.restore()

        self._tentar_ativar(window)
        if self._esta_ativa(window):
            time.sleep(0.3)
            return

        if sys.platform == "win32":
            self._soltar_tecla_alt()
            self._tentar_ativar(window)

        time.sleep(0.3)
        if not self._esta_ativa(window):
            raise WindowActivationError(
                f"janela '{window.title}' encontrada, mas não veio pro primeiro "
                f"plano (Windows recusou SetForegroundWindow mesmo após o "
                f"contorno de foreground lock) — outra aplicação pode estar "
                f"retomando o foco repetidamente."
            )

    @staticmethod
    def _esta_ativa(window, tentativas: int = 5) -> bool:
        """`window.isActive` com tolerância a janela em transição.

        Achado real (29/09/2026): `pygetwindow.getActiveWindow()` levanta
        `PyGetWindowException` (erro 1400, "identificador de janela
        inválido") quando a janela em primeiro plano naquele instante é
        transitória — um menu/diálogo de OUTRO app fechando. Isso derrubava
        `activate()` com um erro que não diz nada sobre a janela-alvo. Tenta
        de novo e, se persistir, responde "não está ativa" (quem chama já
        trata isso com o contorno do foreground lock e, no fim, com
        `WindowActivationError`)."""
        for _ in range(tentativas):
            try:
                return bool(window.isActive)
            except Exception as exc:  # noqa: BLE001 - PyGetWindowException e afins
                logger.debug("isActive levantou (janela em transição?): %s", exc)
                time.sleep(0.2)
        return False

    @staticmethod
    def _tentar_ativar(window) -> None:
        try:
            window.activate()
        except Exception as exc:
            # algumas versões do pygetwindow levantam aviso mesmo quando
            # funciona — por isso a confirmação real é `window.isActive`
            # logo depois, não a ausência de exceção aqui.
            logger.debug("activate() levantou (será reconferido via isActive): %s", exc)

    @staticmethod
    def _soltar_tecla_alt() -> None:
        import ctypes

        user32 = ctypes.windll.user32
        user32.keybd_event(_VK_MENU, 0, 0, 0)
        user32.keybd_event(_VK_MENU, 0, _KEYEVENTF_KEYUP, 0)

    def move_to(self, x: int, y: int) -> None:
        """Move o canto superior esquerdo da janela pra `(x, y)` em pixel de
        tela. Útil pra tirar a janela de um canto problemático antes de
        rodar automação baseada em âncora de imagem por perto.

        Achado real (hp-prime-automation, 01/09/2026): a HP Prime Virtual
        Calculator abriu com `left=676, top=0, width=697, height=775` numa
        tela de `1366x768` — a borda direita (1373) e a inferior (775)
        ficaram alguns pixels PASSANDO do limite da tela, e o canto inferior
        direito é exatamente onde o Windows desenha toasts de notificação
        (inclusive um popup do próprio Claude Code cobriu a âncora usada
        pra localizar uma tecla no meio de um teste — falha sem nenhum erro
        visível na hora, só "âncora não encontrada"). Mover a janela pra um
        canto sem notificação (ex.: `(0, 0)`) evita as duas coisas de uma vez."""
        window = self._window or self.find()
        window.moveTo(x, y)
        time.sleep(0.2)

    def owns_point(self, x: int, y: int) -> bool:
        """`True` se o ponto de tela `(x, y)` pertence a ESTA janela (ou a um
        filho dela) — i.e., uma ação ali cai nela e não numa janela por cima.

        Achado real (hp-prime-automation, 22/09/2026): a HP Prime estava
        ATIVA (`isActive` verdadeiro, `activate()` sem erro), mas a janela
        do app do Claude cobria a mesma região. Todos os cliques da macro
        caíram no Claude, e a cor "lida" do indicador de Shift era a da
        barra lateral dele (16,16,16). Foco não é visibilidade: é preciso
        perguntar ao SO de quem é o pixel (`WindowFromPoint`). Fora do
        Windows devolve `True` (sem como checar)."""
        if sys.platform != "win32":
            return True
        import ctypes
        from ctypes import wintypes

        window = self._window or self.find()
        alvo = getattr(window, "_hWnd", None)
        if alvo is None:
            return True
        user32 = ctypes.windll.user32
        user32.WindowFromPoint.restype = wintypes.HWND
        user32.WindowFromPoint.argtypes = [wintypes.POINT]
        user32.GetAncestor.restype = wintypes.HWND
        user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        hwnd = user32.WindowFromPoint(wintypes.POINT(int(x), int(y)))
        if not hwnd:
            return False
        raiz = user32.GetAncestor(hwnd, 2)  # GA_ROOT
        if int(raiz or 0) == int(alvo):
            return True
        # Menu suspenso/popup do PRÓPRIO app é outra janela top-level, mas do
        # mesmo processo — conta como da janela-alvo (achado real: o menu
        # "Editar" da HP Prime foi barrado como "oclusão" na 1ª versão desta
        # checagem). Janela de OUTRO processo por cima continua barrada.
        return self._pid(raiz or hwnd) == self._pid(alvo)

    def owns_foreground(self) -> bool:
        """`True` se a janela em primeiro plano é do MESMO PROCESSO da
        janela-alvo — i.e., uma tecla enviada agora chega ao app certo.

        Não é o `isActive` que o `activate()` confere: um menu ou diálogo do
        próprio app em primeiro plano é outra janela top-level, mas a tecla
        continua sendo dele — e é justamente pra esses que se manda tecla
        (mesmo critério de processo do `owns_point`). Os dois consumidores
        externos que usam o `WindowManager` sem o `GUIAutomator` escreveram
        esta checagem cada um em ctypes (hp-prime-CK, 29/09/2026; e2e do
        painel-nativo da Tina, 02/10/2026) — ARCHITECTURE.md §9.12.

        Falha fechado: sem janela em primeiro plano (transição, tela
        bloqueada) ou sem PID da janela-alvo, responde `False`. Fora do
        Windows devolve `True` (sem como checar)."""
        if sys.platform != "win32":
            return True
        window = self._window or self.find()
        alvo = getattr(window, "_hWnd", None)
        if alvo is None:
            return True
        frente = self._foreground_hwnd()
        if not frente:
            return False
        pid_alvo = self._pid(alvo)
        return pid_alvo != 0 and self._pid(frente) == pid_alvo

    def ensure_foreground(self) -> None:
        """Garante que a próxima tecla vai pro processo-alvo: se o primeiro
        plano não é dele, ativa (`activate()`, com o contorno de foreground
        lock) e confere de novo. Levanta `WindowOccludedError` se mesmo assim
        o primeiro plano for de outro processo — tecla em janela errada é pior
        que erro: no emulador vira entrada de calculadora, no app do usuário
        vira texto digitado onde ele estava (ARCHITECTURE.md §9.12)."""
        if self.owns_foreground():
            return
        self.activate()
        if not self.owns_foreground():
            raise WindowOccludedError(
                f"o primeiro plano não é do processo da janela '{self.title}' — "
                f"as teclas não serão enviadas"
            )

    @staticmethod
    def _foreground_hwnd() -> int:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        user32.GetForegroundWindow.restype = wintypes.HWND
        return int(user32.GetForegroundWindow() or 0)

    @staticmethod
    def _pid(hwnd) -> int:
        import ctypes
        from ctypes import wintypes

        pid = wintypes.DWORD(0)
        ctypes.windll.user32.GetWindowThreadProcessId(wintypes.HWND(int(hwnd)), ctypes.byref(pid))
        return int(pid.value)

    def geometry(self) -> WindowGeometry:
        window = self._window or self.find()
        return WindowGeometry(left=window.left, top=window.top, width=window.width, height=window.height)

    def is_alive(self) -> bool:
        if self._window is None:
            return False
        try:
            return bool(self._window.title)
        except Exception:
            return False
