"""Tests for the Smithy refine engine (pure Python, seeded RNG)."""
import random

from engine import refine


def test_safe_levels_always_succeed():
    # Levels up to SAFE_LEVEL succeed regardless of the roll.
    for lvl in range(0, refine.SAFE_LEVEL):
        r = refine.attempt(lvl, iron=999, gold=999, rng=random.Random(0))
        assert r.success and r.new_level == lvl + 1


def test_cannot_afford_is_not_attempted():
    r = refine.attempt(0, iron=0, gold=0, rng=random.Random(1))
    assert not r.affordable and r.new_level == 0 and "Need" in r.message


def test_cost_and_chance_curves():
    assert refine.cost(1) == (3, 10)
    assert refine.cost(5) == (15, 50)
    assert refine.success_chance(refine.SAFE_LEVEL) == 1.0
    assert refine.success_chance(refine.SAFE_LEVEL + 1) < 1.0
    # never drops below the floor
    assert refine.success_chance(99) == 0.30


def test_high_level_failure_drops_a_level():
    # Force a failure above the safe band: a 0.0 chance is impossible to beat.
    class AlwaysFail(random.Random):
        def random(self):  # noqa: D401
            return 0.999999
    r = refine.attempt(refine.SAFE_LEVEL + 1, iron=999, gold=999, rng=AlwaysFail())
    assert not r.success and r.new_level == refine.SAFE_LEVEL  # dropped one level
    assert r.affordable                                        # materials still spent


def test_high_level_success_advances():
    class AlwaysWin(random.Random):
        def random(self):
            return 0.0
    r = refine.attempt(refine.SAFE_LEVEL + 1, iron=999, gold=999, rng=AlwaysWin())
    assert r.success and r.new_level == refine.SAFE_LEVEL + 2


def test_cannot_exceed_max():
    r = refine.attempt(refine.MAX_LEVEL, iron=999, gold=999, rng=random.Random(0))
    assert r.at_max and r.new_level == refine.MAX_LEVEL and not r.affordable
