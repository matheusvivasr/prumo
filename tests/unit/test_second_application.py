"""Prova do critério de reutilização — ARCHITECTURE.md §22 / ROADMAP.md
'Segunda aplicação'. Uma aplicação fictícia herda de GUIAutomator sem
tocar em core/, drivers/ ou config/. Se este teste quebrar por causa de
uma mudança em core/ ou drivers/, é sinal de que essas camadas pararam de
ser genéricas — não que a HP Prime mudou (ela nem existe neste repo).
"""

from prumo.core.automator import GUIAutomator
from prumo.core.locator import PointLocator
from prumo.core.state import GUIState
from prumo.drivers.mock import MockDriver
from prumo.drivers.window import WindowGeometry


class _FakeWindow:
    def __init__(self):
        self._geometry = WindowGeometry(left=0, top=0, width=1000, height=1000)

    def find(self):
        return self

    def activate(self):
        pass

    def geometry(self):
        return self._geometry

    def is_alive(self):
        return True


class LegacyApplication(GUIAutomator):
    """Aplicação totalmente fictícia — só adiciona um método semântico
    próprio, chamando exclusivamente a API pública de GUIAutomator."""

    def confirm(self) -> None:
        self.click("ok_button")


def test_second_application_reuses_core_without_modification():
    driver = MockDriver()
    app = LegacyApplication(
        window=_FakeWindow(),
        driver=driver,
        locators={"ok_button": PointLocator(x=0.5, y=0.5)},
        state_detector=lambda: GUIState.READY,
    )

    app.confirm()

    assert driver.actions() == ["click"]
