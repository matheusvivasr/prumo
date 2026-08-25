"""Mapper — ARCHITECTURE.md §18.

Ferramenta de desenvolvimento, fora da biblioteca principal: ajuda a
capturar locators (POINT e REGION) de uma aplicação real, já convertidos
para relativo à janela, e salva no formato de configuração de
`prumo.config`. Também captura **âncoras de imagem** para
`core.anchors.AnchorZone` (§9.2) — um recorte PNG em torno de um ponto,
usado por `InputDriver.locate_on_screen` pra achar esse ponto na tela sem
depender de `window.geometry()`.

Uso:
    python tools/mapper.py "Título da Janela" saida.json

Fluxo: informe o título (substring) da janela já aberta; posicione o mouse
sobre o ponto desejado e pressione ENTER para capturar; dê um nome ao
locator; repita; digite 'sair' para encerrar e salvar o JSON. Locators do
tipo 'point' podem opcionalmente virar âncora (recorte salvo em
`templates/{nome}.png`, ao lado do JSON de saída) — use pra qualquer ponto
que vá servir de âncora de `AnchorZone` (ver ARCHITECTURE.md §9.2: 2 por
zona, em cantos opostos, texto/ícone curto e visualmente único).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from prumo.drivers.window import WindowManager  # noqa: E402

TEMPLATE_MARGIN = 16  # recorte de (2*margem)x(2*margem)px em torno do ponto


def _capture_point() -> Tuple[int, int]:
    import pyautogui

    input("Posicione o mouse e pressione ENTER para capturar...")
    return pyautogui.position()


def _capture_template(point: Tuple[int, int], name: str, templates_dir: Path) -> Path:
    """Recorta um PNG em torno de `point` (coordenada absoluta de tela) e
    salva em `templates_dir/{name}.png`. Requer Pillow (dependência do
    pyautogui, já presente)."""
    import pyautogui
    from PIL import Image

    templates_dir.mkdir(parents=True, exist_ok=True)
    screenshot = pyautogui.screenshot()
    x, y = point
    box = (x - TEMPLATE_MARGIN, y - TEMPLATE_MARGIN, x + TEMPLATE_MARGIN, y + TEMPLATE_MARGIN)
    crop: Image.Image = screenshot.crop(box)
    path = templates_dir / f"{name}.png"
    crop.save(path)
    return path


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

            eh_ancora = input("Também salvar como âncora de imagem? (s/N): ").strip().lower()
            if eh_ancora == "s":
                templates_dir = output_path.parent / "templates"
                caminho = _capture_template(abs_point, name, templates_dir)
                print(f"template salvo em {caminho}")
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
