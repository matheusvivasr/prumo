"""Mapper — ARCHITECTURE.md §18.

Ferramenta de desenvolvimento, fora da biblioteca principal: ajuda a
capturar locators (POINT e REGION) de uma aplicação real, já convertidos
para relativo à janela, e salva no formato de configuração de
`prumo.config`.

Uso:
    python tools/mapper.py "Título da Janela" saida.json

Fluxo: informe o título (substring) da janela já aberta; posicione o mouse
sobre o ponto desejado e pressione ENTER para capturar; dê um nome ao
locator; repita; digite 'sair' para encerrar e salvar o JSON.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from prumo.drivers.window import WindowManager  # noqa: E402


def _capture_point() -> Tuple[int, int]:
    import pyautogui

    input("Posicione o mouse e pressione ENTER para capturar...")
    return pyautogui.position()


def _to_relative(point: Tuple[int, int], window: WindowManager) -> Tuple[float, float]:
    geometry = window.geometry()
    rel_x = (point[0] - geometry.left) / geometry.width
    rel_y = (point[1] - geometry.top) / geometry.height
    return round(rel_x, 4), round(rel_y, 4)


def main() -> None:
    if len(sys.argv) != 3:
        print('uso: python tools/mapper.py "Título da Janela" saida.json')
        raise SystemExit(1)

    title, output_path = sys.argv[1], Path(sys.argv[2])

    window = WindowManager(title)
    window.find()
    window.activate()

    locators: Dict[str, Any] = {}
    if output_path.exists():
        existing = json.loads(output_path.read_text(encoding="utf-8"))
        locators = existing.get("locators", {})
        print(f"{len(locators)} locator(s) existentes carregados de {output_path.name}")

    print(f"Janela ativa: '{title}'. Digite 'sair' a qualquer momento para encerrar.\n")

    while True:
        kind = input("Tipo (point/region/sair): ").strip().lower()
        if kind == "sair":
            break
        if kind not in ("point", "region"):
            print("tipo inválido, use 'point' ou 'region'.")
            continue

        name = input("Nome do locator: ").strip()
        if not name:
            print("nome vazio, ignorando.")
            continue

        if kind == "point":
            abs_point = _capture_point()
            rel_x, rel_y = _to_relative(abs_point, window)
            locators[name] = {"type": "point", "x": rel_x, "y": rel_y}
        else:
            print("Canto superior esquerdo:")
            top_left = _capture_point()
            print("Canto inferior direito:")
            bottom_right = _capture_point()
            rel_x, rel_y = _to_relative(top_left, window)
            rel_x2, rel_y2 = _to_relative(bottom_right, window)
            locators[name] = {
                "type": "region",
                "x": rel_x,
                "y": rel_y,
                "width": round(rel_x2 - rel_x, 4),
                "height": round(rel_y2 - rel_y, 4),
            }

        print(f"'{name}' capturado: {locators[name]}\n")

    config = {
        "schema_version": 1,
        "application": title,
        "window": {"title": title},
        "locators": locators,
    }

    output_path.write_text(json.dumps(config, indent=4, ensure_ascii=False), encoding="utf-8")
    print(f"\n{len(locators)} locator(s) salvos em {output_path}")


if __name__ == "__main__":
    main()
