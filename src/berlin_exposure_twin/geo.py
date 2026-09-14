from __future__ import annotations

from datetime import timedelta
from math import asin, ceil, cos, radians, sin, sqrt

from berlin_exposure_twin.models import Trajectory, TrajectoryPoint

EARTH_RADIUS_M = 6_371_008.8


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(sqrt(a))


def interpolate_segment(
    start: tuple[float, float], end: tuple[float, float], fractions: list[float]
) -> list[tuple[float, float]]:
    lon1, lat1 = start
    lon2, lat2 = end
    return [(lon1 + f * (lon2 - lon1), lat1 + f * (lat2 - lat1)) for f in fractions]


def densify_trajectory(trajectory: Trajectory, *, max_step_m: float = 250.0) -> Trajectory:
    if max_step_m <= 0:
        raise ValueError("max_step_m must be positive")
    points: list[TrajectoryPoint] = []
    for index, (left, right) in enumerate(zip(trajectory.points, trajectory.points[1:], strict=False)):
        if index == 0:
            points.append(left)
        distance = haversine_m(left.latitude, left.longitude, right.latitude, right.longitude)
        steps = max(1, ceil(distance / max_step_m))
        for step in range(1, steps + 1):
            fraction = step / steps
            timestamp = None
            if left.timestamp is not None and right.timestamp is not None:
                timestamp = left.timestamp + timedelta(
                    seconds=(right.timestamp - left.timestamp).total_seconds() * fraction
                )
            points.append(
                TrajectoryPoint(
                    longitude=left.longitude + (right.longitude - left.longitude) * fraction,
                    latitude=left.latitude + (right.latitude - left.latitude) * fraction,
                    timestamp=timestamp,
                )
            )
    return Trajectory(points=points, crs=trajectory.crs)
