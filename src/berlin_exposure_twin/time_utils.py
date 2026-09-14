from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")


class AmbiguousLocalTimeError(ValueError):
    pass


class NonexistentLocalTimeError(ValueError):
    pass


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(UTC)


def berlin_local_to_utc(value: datetime, *, fold: int | None = None) -> datetime:
    if value.tzinfo is not None:
        return ensure_utc(value)
    first = value.replace(tzinfo=BERLIN, fold=0)
    second = value.replace(tzinfo=BERLIN, fold=1)
    first_roundtrip = first.astimezone(UTC).astimezone(BERLIN).replace(tzinfo=None)
    second_roundtrip = second.astimezone(UTC).astimezone(BERLIN).replace(tzinfo=None)
    valid_first = first_roundtrip == value
    valid_second = second_roundtrip == value
    if not valid_first and not valid_second:
        raise NonexistentLocalTimeError(f"Nonexistent Berlin local time: {value.isoformat()}")
    if valid_first and valid_second and first.utcoffset() != second.utcoffset():
        if fold is None:
            raise AmbiguousLocalTimeError(f"Ambiguous Berlin local time: {value.isoformat()}")
        if fold not in (0, 1):
            raise ValueError("fold must be 0 or 1")
        return value.replace(tzinfo=BERLIN, fold=fold).astimezone(UTC)
    return first.astimezone(UTC)
