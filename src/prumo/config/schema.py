"""Validador do mapa — ARCHITECTURE.md §19.

Verifica schema_version, campos obrigatórios e cada locator (tipo válido,
coordenadas no intervalo, região dentro da janela) antes de a configuração
alimentar qualquer automação. Um mapa inválido é rejeitado aqui, não em
tempo de execução da GUI.
"""

from __future__ import annotations

from typing import Any, Dict

from prumo.core.exceptions import LocatorError
from prumo.core.locator import PointLocator, RegionLocator

SUPPORTED_SCHEMA_VERSION = 1


def validate_config(data: Dict[str, Any]) -> None:
    version = data.get("schema_version")
    if version != SUPPORTED_SCHEMA_VERSION:
        raise LocatorError(
            f"schema_version {version!r} não suportada (esperado {SUPPORTED_SCHEMA_VERSION})"
        )

    if not data.get("application"):
        raise LocatorError("config sem campo 'application'")

    window = data.get("window") or {}
    if not window.get("title"):
        raise LocatorError("config sem 'window.title'")

    locators = data.get("locators") or {}
    if not locators:
        raise LocatorError("config sem nenhum locator em 'locators'")

    for name, spec in locators.items():
        _validate_locator_spec(name, spec)


def _validate_locator_spec(name: str, spec: Dict[str, Any]) -> None:
    kind = spec.get("type")
    if kind not in ("point", "region"):
        raise LocatorError(f"locator '{name}': type {kind!r} inválido (use 'point' ou 'region')")
    try:
        if kind == "point":
            PointLocator(x=spec["x"], y=spec["y"])
        else:
            RegionLocator(x=spec["x"], y=spec["y"], width=spec["width"], height=spec["height"])
    except KeyError as exc:
        raise LocatorError(f"locator '{name}': campo obrigatório ausente: {exc}") from exc
    except LocatorError as exc:
        raise LocatorError(f"locator '{name}': {exc}") from exc
