"""Model-table invariants.

These tests exist to stop the single most expensive mistake in this catalogue:
filling a gap by extrapolating from a sibling model.
"""

import pytest

from erdi_lrf.errors import UnknownModelError
from erdi_lrf.models import MODELS, UNPUBLISHED_PROTOCOL, get_model

CATALOGUE_SIZE = 24


def test_catalogue_is_complete_and_honest_about_the_gaps():
    assert len(MODELS) + len(UNPUBLISHED_PROTOCOL) == CATALOGUE_SIZE
    assert set(MODELS) & set(UNPUBLISHED_PROTOCOL) == set()


def test_families_are_split_as_published():
    a = {m for m, s in MODELS.items() if s.family == "A"}
    b = {m for m, s in MODELS.items() if s.family == "B"}
    assert len(a) == 14 and len(b) == 8


@pytest.mark.parametrize("model,unit", [
    ("LRF22VB", "mm"), ("LRF50VB", "mm"),
    ("LRF50H", "cm"), ("LRF100H", "cm"), ("LRF200H", "cm"),
    ("LRF300H", "cm"), ("LRF600H", "cm"), ("LRF1500H", "cm"),
])
def test_family_b_units_are_per_model(model, unit):
    """VB is millimetres, H is centimetres.  Assuming a family unit is 10x wrong."""
    assert get_model(model).unit == unit


def test_metres_per_count_reflects_the_unit():
    assert get_model("LRF22VB").metres_per_count == pytest.approx(0.001)
    assert get_model("LRF100H").metres_per_count == pytest.approx(0.01)
    assert get_model("LR1000E2").metres_per_count == pytest.approx(0.1)


def test_spd1200d03_has_no_default_baud_because_its_manual_conflicts():
    spec = get_model("SPD1200D03")
    assert spec.default_baud is None
    assert any("BAUD CONFLICT" in n for n in spec.notes)


def test_spd1200d03_has_no_scaling_and_says_so():
    spec = get_model("SPD1200D03")
    assert spec.to_metres(1234) is None


def test_a1_series_carries_the_continuous_protocol_hold():
    for model in ("LRF1200A1", "LRF3000A1"):
        assert "PROTOCOL HOLD" in (get_model(model).continuous_hold or "")


def test_lrf1500h_baud_is_the_documented_460800_not_the_extraction_artefact():
    spec = get_model("LRF1500H")
    assert spec.default_baud == 460800
    assert any("extraction artefact" in n for n in spec.notes)


def test_every_model_cites_its_sources():
    for name, spec in MODELS.items():
        assert spec.sources, f"{name} has no manual quotations"


def test_every_model_has_a_range_for_ros_range_messages():
    for name, spec in MODELS.items():
        assert spec.min_range_m is not None, name
        assert spec.max_range_m is not None, name
        assert 0 < spec.min_range_m < spec.max_range_m, name


def test_lookup_is_case_insensitive():
    assert get_model("lrf3000a1").model == "LRF3000A1"
    assert get_model(" LRF100H ").model == "LRF100H"


def test_unpublished_models_fail_loudly_instead_of_guessing():
    for model in UNPUBLISHED_PROTOCOL:
        with pytest.raises(UnknownModelError) as exc:
            get_model(model)
        assert "sibling" in str(exc.value)


def test_unknown_model_lists_what_is_available():
    with pytest.raises(UnknownModelError) as exc:
        get_model("LRF9999Z")
    assert "LRF3000A1" in str(exc.value)


def test_family_a_defaults_to_115200_where_documented():
    for name, spec in MODELS.items():
        if spec.family == "A" and name != "SPD1200D03":
            assert spec.default_baud == 115200, name


def test_family_b_defaults_to_460800():
    for name, spec in MODELS.items():
        if spec.family == "B":
            assert spec.default_baud == 460800, name
