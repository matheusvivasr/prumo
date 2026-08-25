"""Validador do mapa — ARCHITECTURE.md §19.

Ferramenta de desenvolvimento, fora da biblioteca principal: rejeita um
mapa de configuração antes que ele alimente qualquer automação.

Uso:
    python tools/validate_config.py caminho/para/config.json
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from prumo.config.loader import load_config  # noqa: E402
from prumo.core.exceptions import LocatorError  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        print('uso: python tools/validate_config.py caminho/para/config.json')
        raise SystemExit(1)

    path = Path(sys.argv[1])
    try:
        data = load_config(path)
    except LocatorError as exc:
        print(f"INVÁLIDO: {exc}")
        raise SystemExit(1)
    except FileNotFoundError:
        print(f"arquivo não encontrado: {path}")
        raise SystemExit(1)

    print(
        f"OK: '{path.name}' válido — {len(data['locators'])} locator(s), "
        f"janela '{data['window']['title']}'"
    )


if __name__ == "__main__":
    main()
