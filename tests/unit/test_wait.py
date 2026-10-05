"""poll_until — esperar uma condição qualquer, com prazo (ARCHITECTURE.md §9.12)."""

from __future__ import annotations

import pytest

from prumo.core.exceptions import AutomationTimeoutError, UnexpectedStateError
from prumo.core.wait import poll_until


def sequencia(*valores):
    """`cond` que devolve um valor por chamada (o último se repete)."""
    fila = list(valores)

    def cond():
        v = fila.pop(0) if len(fila) > 1 else fila[0]
        if isinstance(v, BaseException):
            raise v
        return v

    return cond


def test_returns_the_truthy_value_itself():
    assert poll_until(sequencia(None, 0, "achei"), timeout=1, what="x", interval=0.001) == "achei"


def test_runs_at_least_once_even_with_zero_timeout():
    assert poll_until(lambda: 42, timeout=0, what="x") == 42


def test_timeout_message_says_what_was_awaited():
    with pytest.raises(AutomationTimeoutError, match="esperando o diálogo de salvar"):
        poll_until(lambda: False, timeout=0.02, what="o diálogo de salvar", interval=0.005)


def test_exception_inside_cond_propagates_by_default():
    with pytest.raises(UnexpectedStateError):
        poll_until(sequencia(UnexpectedStateError("quebrou")), timeout=1, what="x", interval=0.001)


def test_retry_on_turns_not_yet_into_another_attempt():
    cond = sequencia(AutomationTimeoutError("controle ainda não existe"), "apareceu")
    assert poll_until(cond, timeout=1, what="x", interval=0.001, retry_on=(AutomationTimeoutError,)) == "apareceu"


def test_retry_on_reports_the_last_error_when_time_runs_out():
    cond = sequencia(AutomationTimeoutError("controle 'btn-ok' não apareceu"))
    with pytest.raises(AutomationTimeoutError, match="último erro: controle 'btn-ok'"):
        poll_until(cond, timeout=0.02, what="o botão OK", interval=0.005, retry_on=(AutomationTimeoutError,))


def test_retry_on_does_not_swallow_other_exceptions():
    cond = sequencia(UnexpectedStateError("outra coisa"))
    with pytest.raises(UnexpectedStateError):
        poll_until(cond, timeout=1, what="x", interval=0.001, retry_on=(AutomationTimeoutError,))
