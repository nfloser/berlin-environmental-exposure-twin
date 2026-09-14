from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from berlin_exposure_twin.models import Pollutant, Trajectory, TrajectoryPoint


def test_trajectory_rejects_partial_timestamps() -> None:
    with pytest.raises(ValidationError):
        Trajectory(
            points=[
                TrajectoryPoint(longitude=13.4, latitude=52.5, timestamp=datetime.now(UTC)),
                TrajectoryPoint(longitude=13.5, latitude=52.6),
            ]
        )


def test_pollutant_contract_is_stable() -> None:
    assert {member.value for member in Pollutant} == {"no2", "pm10", "pm25", "o3"}
