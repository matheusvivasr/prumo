import pytest

from prumo.core.exceptions import LocatorError
from prumo.core.locator import PointLocator, RegionLocator


def test_point_locator_valid():
    p = PointLocator(x=0.5, y=0.82)
    assert p.x == 0.5 and p.y == 0.82


@pytest.mark.parametrize("x, y", [(-0.1, 0.5), (1.1, 0.5), (0.5, -0.1), (0.5, 1.1)])
def test_point_locator_rejects_out_of_unit_range(x, y):
    with pytest.raises(LocatorError):
        PointLocator(x=x, y=y)


def test_point_locator_is_frozen():
    p = PointLocator(x=0.1, y=0.2)
    with pytest.raises(Exception):
        p.x = 0.5  # type: ignore[misc]


def test_region_locator_valid():
    r = RegionLocator(x=0.1, y=0.05, width=0.8, height=0.3)
    assert r.width == 0.8


def test_region_locator_center():
    r = RegionLocator(x=0.1, y=0.05, width=0.8, height=0.3)
    center = r.center
    assert center == PointLocator(x=0.5, y=0.2)


def test_region_locator_rejects_overflow_x():
    with pytest.raises(LocatorError):
        RegionLocator(x=0.5, y=0.0, width=0.6, height=0.1)


def test_region_locator_rejects_overflow_y():
    with pytest.raises(LocatorError):
        RegionLocator(x=0.0, y=0.5, width=0.1, height=0.6)


def test_to_dict_roundtrip_shape():
    p = PointLocator(x=0.5, y=0.82)
    assert p.to_dict() == {"type": "point", "x": 0.5, "y": 0.82}

    r = RegionLocator(x=0.1, y=0.05, width=0.8, height=0.3)
    assert r.to_dict() == {"type": "region", "x": 0.1, "y": 0.05, "width": 0.8, "height": 0.3}
