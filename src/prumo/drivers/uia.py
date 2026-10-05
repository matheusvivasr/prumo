"""UiaWindow — achar, ler e conferir ponto por UI Automation (ARCHITECTURE.md §9.13).

Primeira fatia do driver de UIA (marco v0.6 do ROADMAP.md). Subiu quando a
UIA ganhou o segundo consumidor (critério §22): o hp-prime-CK (29/09/2026),
que acha os controles do Connectivity Kit por classe/nome, e o e2e do
painel-nativo da Tina (02/10/2026), que acha os controles do WPF por
`AutomationId` e lê o estado depois do gesto. Só subiu o que os DOIS usam:

- a janela de topo de um processo (por título e/ou classe, opcionalmente
  presa a um PID);
- achar controle sob ela, com espera;
- "visível de verdade" = existe E tem área;
- centro do controle, valor (`ValuePattern`);
- de que processo é um ponto da tela (`ControlFromPoint`).

AGIR não é daqui: o gesto continua saindo pelo `InputDriver` (ritmo humano,
soltura confirmada, trava de "o usuário assumiu"). A UIA acha onde e confere
o resultado — a regra do §9.10.

Requer o extra `[uia]` (`uiautomation`, só Windows); o import é preguiçoso.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple

from prumo.core.exceptions import AutomationTimeoutError, UnexpectedStateError, WindowNotFoundError


def _uiautomation():
    import uiautomation

    return uiautomation


class UiaWindow:
    """`name` (título exato) e/ou `class_name` acham a janela de topo; `pid`,
    se dado, exige que ela seja daquele processo — use quando foi você quem o
    abriu e pode haver outra instância. `backend` substitui o módulo
    `uiautomation` (testes)."""

    def __init__(
        self,
        *,
        name: Optional[str] = None,
        class_name: Optional[str] = None,
        pid: Optional[int] = None,
        backend: Any = None,
    ):
        if not name and not class_name:
            raise ValueError("UiaWindow precisa de name ou class_name — sem isso qualquer janela de topo casaria")
        self.name = name
        self.class_name = class_name
        self._pid = pid
        self._backend = backend
        self._root = None

    @property
    def auto(self):
        if self._backend is None:
            self._backend = _uiautomation()
        return self._backend

    def _descricao(self) -> str:
        partes = [f"name={self.name!r}" if self.name else "", f"class_name={self.class_name!r}" if self.class_name else ""]
        if self._pid is not None:
            partes.append(f"pid={self._pid}")
        return ", ".join(p for p in partes if p)

    # --- janela ---------------------------------------------------------

    def connect(self, timeout: float = 3.0) -> "UiaWindow":
        props: Dict[str, Any] = {}
        if self.name:
            props["Name"] = self.name
        if self.class_name:
            props["ClassName"] = self.class_name
        if self._pid is not None:
            pid = self._pid
            props["Compare"] = lambda c, _depth: c.ProcessId == pid
        win = self.auto.WindowControl(searchDepth=1, **props)
        if not win.Exists(timeout, 0.5):
            raise WindowNotFoundError(f"janela ({self._descricao()}) não apareceu na UI Automation em {timeout}s")
        self._root = win
        return self

    @property
    def root(self):
        """A janela de topo. Se ela sumiu desde o `connect()` (app
        reiniciado), procura de novo — com `pid` fixo, uma instância nova
        NÃO é aceita e isso levanta `WindowNotFoundError`."""
        if self._root is None:
            raise UnexpectedStateError(f"UiaWindow ({self._descricao()}) não conectada — chame connect()")
        if not self._root.Exists(0, 0):
            self.connect()
        return self._root

    @property
    def pid(self) -> int:
        """O informado no construtor ou, sem ele, o da janela achada."""
        return self._pid if self._pid is not None else int(self.root.ProcessId)

    # --- achar e ler ------------------------------------------------------

    def find(self, *, timeout: float = 6.0, **props):
        """Controle sob a janela com as propriedades dadas (`AutomationId=`,
        `Name=`, `ClassName=`...), esperando até `timeout`."""
        c = self.auto.Control(searchFromControl=self.root, **props)
        if not c.Exists(timeout, 0.2):
            raise AutomationTimeoutError(f"controle {props} não apareceu em {timeout}s")
        return c

    def is_visible(self, **props) -> bool:
        """Existe AGORA e tem área na tela. Um elemento `Collapsed` do WPF
        continua na árvore da UIA, com área zero — "existe" sozinho mente."""
        c = self.auto.Control(searchFromControl=self.root, **props)
        if not c.Exists(0, 0):
            return False
        r = c.BoundingRectangle
        return r.width() > 0 and r.height() > 0

    def center(self, control, label: str = "") -> Tuple[int, int]:
        """Centro do controle em pixel de tela — o ponto que o `InputDriver`
        vai clicar. Sem área (escondido, fora da janela): `UnexpectedStateError`."""
        r = control.BoundingRectangle
        if r.width() <= 0 or r.height() <= 0:
            raise UnexpectedStateError(f"'{label or control}' sem área na tela (escondido ou fora da janela)")
        return ((r.left + r.right) // 2, (r.top + r.bottom) // 2)

    def value(self, control) -> str:
        return control.GetValuePattern().Value

    # --- conferir ponto ---------------------------------------------------

    def owns_point(self, x: int, y: int) -> bool:
        """`True` se o controle sob `(x, y)` é do processo desta janela — a
        segunda opinião do `WindowManager.owns_point` (§9.9), vista pela
        árvore de acessibilidade. A UIA às vezes levanta `COMError`
        intermitente aqui: tenta uma segunda vez antes de deixar subir."""
        try:
            dono = self.auto.ControlFromPoint(x, y)
        except Exception:  # noqa: BLE001 - COMError do comtypes, sem import direto
            time.sleep(0.2)
            dono = self.auto.ControlFromPoint(x, y)
        return dono is not None and int(dono.ProcessId) == self.pid
