"""Exceções específicas do framework — ARCHITECTURE.md §13.

`AutomationTimeoutError` (não `TimeoutError`) para não sombrear a exceção
built-in do Python, que várias bibliotecas de I/O (socket, asyncio) esperam
poder capturar sem ambiguidade.
"""


class AutomationError(Exception):
    """Base de todas as exceções do prumo."""


class WindowNotFoundError(AutomationError):
    """Janela-alvo não encontrada ou desapareceu."""


class WindowActivationError(AutomationError):
    """Janela encontrada, mas não foi possível trazê-la pro primeiro plano
    (Windows recusou `SetForegroundWindow`, mesmo após o contorno de
    foreground lock) — outro processo pode estar retomando o foco."""


class WindowOccludedError(AutomationError):
    """A janela-alvo está ativa, mas o ponto onde a ação cairia pertence a
    OUTRA janela por cima (ex.: uma janela "sempre no topo"). Ter foco não
    garante estar visível — ARCHITECTURE.md §9.9."""


class InputReleaseError(AutomationError):
    """O SO não confirmou que um botão do mouse ou tecla foi solto depois
    da ação — seguir em frente com algo pressionado corromperia as próximas
    ações (ARCHITECTURE.md §9.9)."""


class LocatorError(AutomationError):
    """Locator inválido, ausente do mapa, ou mapa de configuração malformado."""


class AutomationTimeoutError(AutomationError):
    """Uma espera por estado ou condição excedeu o timeout configurado."""


class UnexpectedStateError(AutomationError):
    """O estado da aplicação é desconhecido ou incompatível com a operação."""


class PopupError(AutomationError):
    """Uma interrupção (popup) não pôde ser tratada."""


class RecoveryError(AutomationError):
    """A recuperação automática se esgotou sem retornar a READY."""
