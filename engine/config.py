"""Engine configuration.

These are all the "balance knobs" of the game (starting stats, the XP curve,
world size, rewards...). The engine treats them as plain inputs.

In the real app these values come from the database (the `GameConfig` row, edited
in the Django admin) and are converted into one of these objects by the bridge
(`game/services.load_config`). Nothing here is hardcoded into the game rules —
the rules just read whatever config they are handed.
"""
from dataclasses import dataclass


@dataclass
class EngineConfig:
    # New-character starting stats
    start_hp: int = 30
    start_attack: int = 8
    start_defense: int = 4
    start_gold: int = 20

    # World generation
    grid_size: int = 10
    monster_count: int = 6        # legacy; monsters are random encounters now
    treasure_count: int = 3
    encounter_rate: float = 0.18  # chance of a random battle per step

    # Leveling curve
    xp_base: int = 50        # XP required to go from level 1 -> 2
    xp_growth: float = 1.5   # each level needs this much more than the last
    stat_growth: int = 3     # attack/defense gained per level (HP gains 2x this)

    # Town / rewards
    rest_cost: int = 10
    treasure_gold_min: int = 5
    treasure_gold_max: int = 25
