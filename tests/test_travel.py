"""Pure-engine tests for World-Map travel time."""
from engine import travel


def test_center_is_minimum_time():
    assert travel.travel_seconds(50, 50) == travel.MIN_TRAVEL_SECONDS


def test_farther_takes_longer():
    near = travel.travel_seconds(55, 50)     # 5 units out
    far = travel.travel_seconds(90, 50)      # 40 units out
    assert far > near
    assert far == int(round(40 * travel.SECONDS_PER_UNIT))


def test_distance_is_symmetric_euclidean():
    assert travel.distance(0, 0, 3, 4) == 5
    assert travel.distance_from_center(50, 50) == 0
