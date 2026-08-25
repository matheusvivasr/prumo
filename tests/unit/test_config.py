import json
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
