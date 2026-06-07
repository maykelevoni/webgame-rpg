"""Monsters and how one is chosen to fight.

A `Monster` is a template (its base stats). The list of monsters in the game lives
in the database and is editable in the admin; the bridge turns those rows into
`Monster` objects and hands them here. Plugins may add more monsters to the list.
"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class Monster:
    key: str
    name: str
    max_hp: int
    attack: int
    defense: int
    gold_reward: int
    xp_reward: int
    min_level: int = 1
    icon: str = ""  # sprite name for display (set from the DB), e.g. "tile_0108"


def pick_monster(
    spawn_list: list[Monster],
    level: int,
    rng: random.Random | None = None,
) -> Monster | None:
    """Choose a random monster the player's ``level`` is allowed to meet.

    Only monsters whose ``min_level`` is at or below the player's level are
    eligible. Returns None if the list is empty.
    """
    if not spawn_list:
        return None
    rng = rng or random.Random()
    eligible = [m for m in spawn_list if m.min_level <= level]
    # If the player is somehow below every monster's min_level, fall back to all.
    return rng.choice(eligible or spawn_list)
