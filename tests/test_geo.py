from datetime import UTC, datetime, timedelta

import pytest

from berlin_exposure_twin.geo import densify_trajectory, haversine_m
from berlin_exposure_twin.models import Trajectory, TrajectoryPoint


def test_haversine_zero_distance() -> None:
    assert haversine_m(52.5, 13.4, 52.5, 13.4) == pytest.approx(0.0)


def test_densify_trajectory_interpolates_timestamps_without_inventing_speed() -> None:
    start = datetime(2026, 1, 1, 12, tzinfo=UTC)
    trajectory = Trajectory(
        points=[
            TrajectoryPoint(longitude=13.4, latitude=52.5, timestamp=start),
            TrajectoryPoint(
                longitude=13.42,
                latitude=52.5,
                timestamp=start + timedelta(minutes=10),
            ),
        ]
    )
    dense = densify_trajectory(trajectory, max_step_m=500)
    assert len(dense.points) > 2
    assert dense.points[0].timestamp == start
    assert dense.points[-1].timestamp == start + timedelta(minutes=10)
