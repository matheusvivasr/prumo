"""Carrega o mapa de configuração — ARCHITECTURE.md §7-§8.

`load_config` detecta chaves duplicadas no JSON (que `json.load` normal
silenciaria, mantendo só a última) e valida o resultado com
`config.schema.validate_config` antes de devolvê-lo.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

from prumo.config.schema import validate_config
from prumo.core.exceptions import LocatorError
from prumo.core.locator import Locator, PointLocator, RegionLocator


def _no_duplicate_keys(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LocatorError(f"chave duplicada no mapa de configuração: '{key}'")
        result[key] = value
    return result


def load_config(path: Union[str, Path]) -> Dict[str, Any]:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f, object_pairs_hook=_no_duplicate_keys)
    validate_config(data)
    return data


def build_locators(data: Dict[str, Any]) -> Dict[str, Locator]:
    """Assume `data` já validado por `load_config`/`validate_config`."""
    locators: Dict[str, Locator] = {}
    for name, spec in data["locators"].items():
        if spec["type"] == "point":
            locators[name] = PointLocator(x=spec["x"], y=spec["y"])
        else:
            locators[name] = RegionLocator(
                x=spec["x"], y=spec["y"], width=spec["width"], height=spec["height"]
            )
    return locators


def window_title(data: Dict[str, Any]) -> str:
    return data["window"]["title"]
