"""Pure World-Map travel math. No Django — the bridge passes plain coordinates in.

The World Map is a 0-100 square; the Castle is the centre you set out from. Travelling
to a node takes time proportional to its distance from the centre — far places are a
longer march (and, by design, richer/tougher). Deterministic and unit-tested.
"""
from __future__ import annotations

import math

CENTER = (50, 50)              # the Castle sits at the middle of the World Map
SECONDS_PER_UNIT = 4.0         # march time per unit of map distance
MIN_TRAVEL_SECONDS = 10        # even the nearest node takes a moment


def distance(ax: float, ay: float, bx: float, by: float) -> float:
    """Straight-line distance between two World-Map points."""
    return math.hypot(bx - ax, by - ay)


def distance_from_center(x: float, y: float) -> float:
    return distance(CENTER[0], CENTER[1], x, y)


def travel_seconds(x: float, y: float) -> int:
    """Seconds to march from the Castle (centre) to the node at (x, y)."""
    return travel_seconds_from(CENTER[0], CENTER[1], x, y)


def travel_seconds_from(ox: float, oy: float, x: float, y: float) -> int:
    """Seconds to march from (ox, oy) to (x, y) — distance-proportional."""
    secs = distance(ox, oy, x, y) * SECONDS_PER_UNIT
    return max(MIN_TRAVEL_SECONDS, int(round(secs)))
