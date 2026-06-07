"""Leveling math.

Kept separate so the "how much XP / how much growth" rules are easy to find and
tweak. All values come from the config object (which comes from the DB), so you
can rebalance progression without touching this code.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # import only for type hints; avoids a runtime import cycle
    from engine.character import Character
    from engine.config import EngineConfig


def xp_to_next(level: int, xp_base: int, xp_growth: float) -> int:
    """XP needed to advance FROM ``level`` to the next one.

    Level 1 needs ``xp_base``; each level after costs ``xp_growth`` times more.
    Example with base=50, growth=1.5: L1->2 = 50, L2->3 = 75, L3->4 = 112, ...
    """
    return int(xp_base * (xp_growth ** (level - 1)))


def apply_level_ups(character: "Character", cfg: "EngineConfig") -> int:
    """Spend the character's accumulated XP on as many level-ups as it affords.

    Returns the number of levels gained. Surplus XP is carried over toward the
    next level. Leveling up raises stats and fully heals the character.
    """
    levels_gained = 0
    while character.xp >= xp_to_next(character.level, cfg.xp_base, cfg.xp_growth):
        cost = xp_to_next(character.level, cfg.xp_base, cfg.xp_growth)
        character.xp -= cost
        character.level += 1
        character.base_attack += cfg.stat_growth
        character.base_defense += cfg.stat_growth
        character.max_hp += cfg.stat_growth * 2  # HP grows faster than offence
        character.hp = character.max_hp           # reward: full heal on level up
        levels_gained += 1
    return levels_gained
