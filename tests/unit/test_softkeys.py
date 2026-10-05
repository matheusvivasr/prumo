import pytest
from prumo.core.softkeys import SoftkeyRow
from prumo.drivers.window import WindowGeometry


def _geometry():
    return WindowGeometry(left=1000, top=200, width=343, height=741)


def test_resolve_centers_each_slot_proportionally_to_width():
    row = SoftkeyRow(count=6, y_offset=298, geometry_key=_geometry)

    x0, y0 = row.resolve(0)
    x5, y5 = row.resolve(5)

    slot_width = 343 / 6
    assert x0 == 1000 + round(slot_width * 0.5)
    assert x5 == 1000 + round(slot_width * 5.5)
    assert y0 == y5 == 200 + 298


def test_resolve_uses_current_geometry_each_call():
    geometries = [WindowGeometry(left=0, top=0, width=600, height=800)]
    row = SoftkeyRow(count=6, y_offset=298, geometry_key=lambda: geometries[0])

    x_before, _ = row.resolve(0)
    geometries[0] = WindowGeometry(left=100, top=0, width=600, height=800)
    x_after, _ = row.resolve(0)

    assert x_after == x_before + 100


def test_resolve_rejects_out_of_range_index():
    row = SoftkeyRow(count=6, y_offset=298, geometry_key=_geometry)

    with pytest.raises(ValueError):
        row.resolve(6)

    with pytest.raises(ValueError):
        row.resolve(-1)


@pytest.mark.parametrize("indice", [2.5, True, "3"], ids=["meio", "bool", "texto"])
def test_a_non_integer_index_is_refused_instead_of_clicking_between_keys(indice):
    # 2.5 resolvia para a divisa exata entre F3 e F4
    linha = SoftkeyRow(count=6, y_offset=40, geometry_key=lambda: WindowGeometry(0, 0, 600, 800))
    with pytest.raises(ValueError, match="inteiro"):
        linha.resolve(indice)


@pytest.mark.parametrize("count", [0, -1, 2.0, True])
def test_a_row_needs_at_least_one_key(count):
    with pytest.raises(ValueError, match="count"):
        SoftkeyRow(count=count, y_offset=40, geometry_key=lambda: WindowGeometry(0, 0, 600, 800))
