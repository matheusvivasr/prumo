import pytest

from prumo.core.anchors import Anchor, AnchorZone
from prumo.core.exceptions import LocatorError
from prumo.core.locator import PointLocator


def _zone(screen_positions, geometry_key=lambda: "g1"):
    calls = []

    def locate(template_path):
        calls.append(template_path)
        return screen_positions.get(template_path)

    anchor1 = Anchor(locator=PointLocator(x=0.1, y=0.2), template_path="a.png")
    anchor2 = Anchor(locator=PointLocator(x=0.9, y=0.8), template_path="b.png")
    zone = AnchorZone(anchor1, anchor2, locate=locate, geometry_key=geometry_key)
    return zone, calls


def test_resolve_reproduces_the_anchors_themselves():
    zone, _ = _zone({"a.png": (100.0, 200.0), "b.png": (900.0, 800.0)})

    assert zone.resolve(PointLocator(x=0.1, y=0.2)) == (100, 200)
    assert zone.resolve(PointLocator(x=0.9, y=0.8)) == (900, 800)


def test_resolve_interpolates_a_third_point_linearly():
    zone, _ = _zone({"a.png": (100.0, 200.0), "b.png": (900.0, 800.0)})

    # ponto no meio das duas ancoras -> pixel no meio tambem (transformacao linear)
    x, y = zone.resolve(PointLocator(x=0.5, y=0.5))

    assert x == round(100 + (900 - 100) * (0.5 - 0.1) / (0.9 - 0.1))
    assert y == round(200 + (800 - 200) * (0.5 - 0.2) / (0.8 - 0.2))


def test_transform_is_cached_until_geometry_changes():
    key = {"v": "g1"}
    zone, calls = _zone(
        {"a.png": (100.0, 200.0), "b.png": (900.0, 800.0)},
        geometry_key=lambda: key["v"],
    )

    zone.resolve(PointLocator(x=0.5, y=0.5))
    zone.resolve(PointLocator(x=0.3, y=0.7))
    assert calls == ["a.png", "b.png"]  # só localizou 1 vez, resultado reaproveitado

    key["v"] = "g2"  # simula janela mudando de posição/tamanho/modo
    zone.resolve(PointLocator(x=0.5, y=0.5))
    assert calls == ["a.png", "b.png", "a.png", "b.png"]  # refez a busca


def test_anchor_not_found_raises_locator_error_without_guessing():
    zone, _ = _zone({"a.png": (100.0, 200.0)})  # b.png "não encontrado"

    with pytest.raises(LocatorError):
        zone.resolve(PointLocator(x=0.5, y=0.5))


def test_anchors_with_same_x_or_y_are_rejected():
    anchor1 = Anchor(locator=PointLocator(x=0.5, y=0.1), template_path="a.png")
    anchor2 = Anchor(locator=PointLocator(x=0.5, y=0.9), template_path="b.png")  # mesmo x
    zone = AnchorZone(
        anchor1, anchor2,
        locate=lambda p: (0.0, 0.0),
        geometry_key=lambda: "g1",
    )

    with pytest.raises(LocatorError):
        zone.resolve(PointLocator(x=0.5, y=0.5))
