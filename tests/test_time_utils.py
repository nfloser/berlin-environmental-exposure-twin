from datetime import UTC, datetime

import pytest

from berlin_exposure_twin.time_utils import (
    AmbiguousLocalTimeError,
    NonexistentLocalTimeError,
    berlin_local_to_utc,
)


def test_summer_time_converts_to_utc() -> None:
    assert berlin_local_to_utc(datetime(2026, 7, 1, 12)).hour == 10


def test_spring_dst_gap_is_rejected() -> None:
    with pytest.raises(NonexistentLocalTimeError):
        berlin_local_to_utc(datetime(2026, 3, 29, 2, 30))


def test_autumn_dst_fold_requires_explicit_choice() -> None:
    local = datetime(2026, 10, 25, 2, 30)
    with pytest.raises(AmbiguousLocalTimeError):
        berlin_local_to_utc(local)
    assert berlin_local_to_utc(local, fold=0) == datetime(2026, 10, 25, 0, 30, tzinfo=UTC)
    assert berlin_local_to_utc(local, fold=1) == datetime(2026, 10, 25, 1, 30, tzinfo=UTC)
