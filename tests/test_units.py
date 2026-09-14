import pytest

from berlin_exposure_twin.units import UnitError, concentration_to_ug_m3


def test_mg_to_ug_conversion() -> None:
    assert concentration_to_ug_m3(0.021, "mg/m³") == pytest.approx(21.0)


def test_unknown_unit_is_rejected() -> None:
    with pytest.raises(UnitError):
        concentration_to_ug_m3(2.0, "ppm")
