"""The Arduino model table (arduino/ErdiLRF/src/ErdiLRF.cpp) must agree with the Python catalogue.

The two drivers are transcribed separately; this test stops them drifting apart (11-07: Python 0.1.3 gained
LRF10VB while the Arduino table still lacked it).
"""
import re
from pathlib import Path

import pytest

from erdi_lrf.models import CAP_SET_BAUD, CAP_START_STOP, MODELS

SRC = Path(__file__).resolve().parents[2] / "arduino" / "ErdiLRF" / "src"
ROW = re.compile(
    r'^\s*\{\s*"(?P<name>[A-Z0-9]+)"\s*,\s*ERDI_FAMILY_(?P<fam>[AB])\s*,\s*(?P<baud>\d+)UL\s*,\s*(?P<len>\d+)\s*,\s*'
    r'(?P<dist>\d+)\s*,\s*ERDI_UNIT_(?P<unit>[A-Z]+)\s*,\s*(?P<oor>\d+)UL\s*,\s*(?P<min>\d+)\s*,\s*(?P<max>\d+)UL\s*,\s*'
    r'(?P<ss>[01])\s*,\s*(?P<hold>[01])\s*\}', re.M)
UNIT = {"DECIMETRE": ("m", 10.0), "CENTIMETRE": ("cm", 1.0), "MILLIMETRE": ("mm", 1.0), "UNDOCUMENTED": (None, None)}


def _table():
    text = (SRC / "ErdiLRF.cpp").read_text(encoding="utf-8")
    return {m["name"]: m for m in ROW.finditer(text)}


def _enum_names():
    text = (SRC / "ErdiLRF.h").read_text(encoding="utf-8")
    body = text[text.index("enum ErdiModel"):text.index("ERDI_MODEL_COUNT")]
    return re.findall(r"ERDI_([A-Z0-9]+)\s*(?:=\s*\d+\s*)?,", body)


def test_arduino_table_covers_exactly_the_python_models():
    assert set(_table()) == set(MODELS)


def test_enum_order_matches_table_order():
    # kModels[] is indexed by the enum value, so a different order silently returns the wrong model.
    assert _enum_names() == list(_table())


@pytest.mark.parametrize("name", sorted(MODELS))
def test_row_matches_python_spec(name):
    row, spec = _table()[name], MODELS[name]
    assert row["fam"] == spec.family
    assert int(row["baud"]) == (spec.default_baud or 0)
    assert int(row["len"]) == spec.frame_len
    if spec.family == "B":
        assert int(row["dist"]) == spec.distance_bytes
    assert UNIT[row["unit"]] == ((spec.unit, spec.raw_scale) if spec.unit else (None, None))
    assert int(row["oor"]) == (spec.out_of_range_raw or 0)
    if spec.min_range_m is not None:
        assert int(row["min"]) == round(spec.min_range_m * 100)
    assert int(row["max"]) == round(spec.max_range_m * 100)
    if spec.family == "B":
        assert (row["ss"] == "1") == spec.supports(CAP_START_STOP)


def test_lrf10vb_arduino_values_from_spec_v3_0():
    row = _table()["LRF10VB"]
    assert (row["fam"], int(row["baud"]), int(row["len"]), int(row["dist"]), row["unit"]) == ("B", 460800, 4, 2, "MILLIMETRE")
    assert (int(row["oor"]), int(row["min"]), int(row["max"]), row["ss"]) == (65535, 5, 900, "1")
    assert not MODELS["LRF10VB"].supports(CAP_SET_BAUD)
    cpp = (SRC / "ErdiLRF.cpp").read_text(encoding="utf-8")
    assert "_model == ERDI_LRF10VB" in cpp, "setBaudB must refuse LRF10VB (no baud frame in its manual)"
