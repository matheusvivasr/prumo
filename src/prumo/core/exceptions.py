"""Exceções específicas do framework — ARCHITECTURE.md §13.

`AutomationTimeoutError` (não `TimeoutError`) para não sombrear a exceção
built-in do Python, que várias bibliotecas de I/O (socket, asyncio) esperam
poder capturar sem ambiguidade.
"""


class AutomationError(Exception):
    """Base de todas as exceções do prumo."""


class WindowNotFoundError(AutomationError):
    """Janela-alvo não encontrada ou desapareceu."""


class AmbiguousWindowError(AutomationError):
    """Mais de uma janela casa com a busca e nada desempata (título exato,
    PID). Agir em qualquer uma seria apostar qual é a certa. NÃO herda de
    `WindowNotFoundError` de propósito: quem trata "não achei" abrindo o app
    abriria mais uma instância e pioraria o problema."""


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


class UserTakeoverError(AutomationError):
    """O usuário tomou a frente — apertou a tecla de abortar ou mexeu no
    mouse entre dois gestos da automação. Não é defeito do app: é a
    automação parando de disputar o mouse com quem é dono dele
    (ARCHITECTURE.md §9.12)."""


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
