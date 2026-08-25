"""Locators — ARCHITECTURE.md §6.

Um locator é uma localização lógica da interface, relativa à janela
(0.0-1.0). Não conhece pixels absolutos, não executa ações, é imutável e
serializável. Nada aqui sabe que existe uma HP Prime ou qualquer outra
aplicação-alvo.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Union

from prumo.core.exceptions import LocatorError


def _validate_unit(field: str, value: float) -> None:
    if not (0.0 <= value <= 1.0):
        raise LocatorError(f"'{field}'={value} fora do intervalo [0.0, 1.0]")


@dataclass(frozen=True)
class PointLocator:
    x: float
    y: float

    def __post_init__(self) -> None:
        _validate_unit("x", self.x)
        _validate_unit("y", self.y)

    def to_dict(self) -> dict[str, Any]:
        return {"type": "point", **asdict(self)}


@dataclass(frozen=True)
class RegionLocator:
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        _validate_unit("x", self.x)
        _validate_unit("y", self.y)
        _validate_unit("width", self.width)
        _validate_unit("height", self.height)
        if self.x + self.width > 1.0:
            raise LocatorError(f"região ultrapassa a janela: x({self.x}) + width({self.width}) > 1.0")
        if self.y + self.height > 1.0:
            raise LocatorError(f"região ultrapassa a janela: y({self.y}) + height({self.height}) > 1.0")

    @property
    def center(self) -> PointLocator:
        return PointLocator(x=self.x + self.width / 2, y=self.y + self.height / 2)

    def to_dict(self) -> dict[str, Any]:
        return {"type": "region", **asdict(self)}


Locator = Union[PointLocator, RegionLocator]
