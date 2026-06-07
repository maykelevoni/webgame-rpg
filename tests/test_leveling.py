"""Tests for the leveling math — pure engine, no database needed."""
from engine.character import Character
from engine.config import EngineConfig
from engine.leveling import xp_to_next


def cfg(**over):
    return EngineConfig(**over)


def test_xp_to_next_follows_the_curve():
    assert xp_to_next(1, xp_base=50, xp_growth=1.5) == 50
    assert xp_to_next(2, xp_base=50, xp_growth=1.5) == 75
    assert xp_to_next(3, xp_base=50, xp_growth=1.5) == 112


def test_gaining_enough_xp_levels_up_and_grows_stats():
    c = Character(name="Hero", base_attack=8, base_defense=4, max_hp=30, hp=30)
    levels = c.gain_xp(50, cfg(xp_base=50, xp_growth=1.5, stat_growth=3))
    assert levels == 1
    assert c.level == 2
    assert c.base_attack == 11   # +stat_growth
    assert c.base_defense == 7   # +stat_growth
    assert c.max_hp == 36        # +2*stat_growth
    assert c.hp == c.max_hp      # full heal on level up


def test_surplus_xp_is_carried_over():
    c = Character(name="Hero")
    # 60 XP: 50 spent reaching level 2, 10 left over.
    c.gain_xp(60, cfg(xp_base=50, xp_growth=1.5))
    assert c.level == 2
    assert c.xp == 10


def test_multiple_levels_at_once():
    c = Character(name="Hero")
    # Enough for two level-ups (50 + 75 = 125).
    levels = c.gain_xp(130, cfg(xp_base=50, xp_growth=1.5))
    assert levels == 2
    assert c.level == 3
    assert c.xp == 5
