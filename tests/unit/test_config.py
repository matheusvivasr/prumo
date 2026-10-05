from pathlib import Path

import pytest

from prumo.config.loader import build_locators, load_config, window_title
from prumo.config.schema import validate_config
from prumo.core.exceptions import LocatorError
from prumo.core.locator import PointLocator, RegionLocator

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "sample_config.json"


def test_load_config_valid_fixture():
    data = load_config(FIXTURE)
    assert data["application"] == "Fake Calculator"
    assert window_title(data) == "Fake Calculator"


def test_build_locators_from_fixture():
    data = load_config(FIXTURE)
    locators = build_locators(data)
    assert locators["enter_key"] == PointLocator(x=0.50, y=0.82)
    assert locators["display"] == RegionLocator(x=0.10, y=0.05, width=0.80, height=0.30)


def test_rejects_wrong_schema_version():
    with pytest.raises(LocatorError):
        validate_config({"schema_version": 2, "application": "x", "window": {"title": "x"},
                          "locators": {"a": {"type": "point", "x": 0.1, "y": 0.1}}})


def test_rejects_missing_window_title():
    with pytest.raises(LocatorError):
        validate_config({"schema_version": 1, "application": "x", "window": {},
                          "locators": {"a": {"type": "point", "x": 0.1, "y": 0.1}}})


def test_rejects_empty_locators():
    with pytest.raises(LocatorError):
        validate_config({"schema_version": 1, "application": "x", "window": {"title": "x"}, "locators": {}})


def test_rejects_invalid_locator_type():
    with pytest.raises(LocatorError):
        validate_config({
            "schema_version": 1, "application": "x", "window": {"title": "x"},
            "locators": {"a": {"type": "circle", "x": 0.1, "y": 0.1}},
        })


def test_rejects_locator_out_of_range():
    with pytest.raises(LocatorError):
        validate_config({
            "schema_version": 1, "application": "x", "window": {"title": "x"},
            "locators": {"a": {"type": "point", "x": 1.5, "y": 0.1}},
        })


def test_rejects_duplicate_locator_key(tmp_path):
    raw = (
        '{"schema_version": 1, "application": "x", "window": {"title": "x"}, '
        '"locators": {"a": {"type": "point", "x": 0.1, "y": 0.1}, '
        '"a": {"type": "point", "x": 0.2, "y": 0.2}}}'
    )
    path = tmp_path / "dup.json"
    path.write_text(raw, encoding="utf-8")
    with pytest.raises(LocatorError):
        load_config(path)


def _mapa(spec_a):
    return {"schema_version": 1, "application": "x", "window": {"title": "x"}, "locators": {"a": spec_a}}


def test_a_config_saved_by_notepad_with_bom_still_loads(tmp_path):
    # o Bloco de Notas do Windows salva UTF-8 com BOM; o json puro recusava
    path = tmp_path / "com_bom.json"
    original = FIXTURE.read_bytes()
    assert not original.startswith(b"\xef\xbb\xbf")        # o fixture em si não tem BOM
    path.write_bytes(b"\xef\xbb\xbf" + original)
    assert load_config(path) == load_config(FIXTURE)


@pytest.mark.parametrize("valor", [True, False], ids=["true", "false"])
def test_a_boolean_is_not_a_coordinate(valor):
    # True vale 1 em Python: passava como o canto da janela
    with pytest.raises(LocatorError, match="locator 'a'.*não é número"):
        validate_config(_mapa({"type": "point", "x": valor, "y": 0.1}))


def test_a_string_coordinate_names_the_locator_instead_of_a_raw_type_error():
    with pytest.raises(LocatorError, match="locator 'a'.*'0.5'"):
        validate_config(_mapa({"type": "point", "x": "0.5", "y": 0.1}))


def test_a_json_that_is_not_an_object_is_rejected_clearly(tmp_path):
    path = tmp_path / "lista.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(LocatorError, match="objeto JSON"):
        load_config(path)


def test_a_locator_that_is_not_an_object_is_rejected_clearly():
    with pytest.raises(LocatorError, match="locator 'a': precisa ser um objeto"):
        validate_config(_mapa([0.1, 0.2]))
