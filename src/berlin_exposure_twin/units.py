from __future__ import annotations


class UnitError(ValueError):
    """Raised when an unsupported or incompatible unit is encountered."""


def concentration_to_ug_m3(value: float, unit: str) -> float:
    normalized = unit.strip().replace("ug/m3", "µg/m³").replace("mg/m3", "mg/m³")
    if normalized == "µg/m³":
        return value
    if normalized == "mg/m³":
        return value * 1000.0
    raise UnitError(f"Unsupported concentration unit: {unit}")
