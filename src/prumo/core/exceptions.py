"""Exceções específicas do framework — ARCHITECTURE.md §13.

`AutomationTimeoutError` (não `TimeoutError`) para não sombrear a exceção
built-in do Python, que várias bibliotecas de I/O (socket, asyncio) esperam
poder capturar sem ambiguidade.
"""


class AutomationError(Exception):
    """Base de todas as exceções do prumo."""


class WindowNotFoundError(AutomationError):
    """Janela-alvo não encontrada ou desapareceu."""


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
