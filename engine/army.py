"""Pure army + raid resolution for the second loop. No Django, no I/O — the bridge
(``game/services.py``) passes plain numbers in and reads the result out, so everything
here is deterministic and unit-tested.

The hero **personally leads** the raid: his attack plus the army's size make up its
power, pitted against a target's fixed defense. Win or lose, **only the survivors
come home**; if the army is overwhelmed the **hero himself can fall** and must recover
before adventuring again. Soldiers cost meat to train and keep eating meat every
minute (see ``UPKEEP_MEAT_PER_MIN``, consumed in ``village.tick``).
"""
from __future__ import annotations

from dataclasses import dataclass

# --- balance (tunable; lives here so it's all in one place) ----------------
TRAIN_MEAT_COST = 12          # meat to train one soldier
UPKEEP_MEAT_PER_MIN = 0.15    # meat eaten per soldier per minute (food upkeep)
TROOP_POWER = 6               # each soldier's contribution to army power


@dataclass(frozen=True)
class RaidTarget:
    """An NPC village/camp you can raid. (Real players' villages will be the same
    shape later — that's how this code becomes async PvP for free.)"""
    key: str
    name: str
    defense: int
    loot_gold: int
    loot: dict                # resource -> amount granted on a win
    emoji: str = "🏚️"
    world_x: int = 50         # position on the strategic World Map
    world_y: int = 50


@dataclass
class RaidResult:
    target: str
    win: bool
    troops_sent: int
    survivors: int
    troops_lost: int
    hero_died: bool
    loot_gold: int
    loot: dict
    message: str


def army_power(troops: int, hero_attack: int) -> int:
    """Total raiding power: the army plus the hero leading it."""
    return max(0, troops) * TROOP_POWER + max(0, hero_attack)


def train_cost(count: int) -> int:
    """Meat needed to train ``count`` soldiers."""
    return max(0, count) * TRAIN_MEAT_COST


def resolve_raid(troops: int, hero_attack: int, target: RaidTarget, rng) -> RaidResult:
    """Resolve a raid on ``target`` led by the hero with ``troops`` soldiers.

    Win is power-vs-defense with a luck roll. Casualties scale with how outmatched
    the army was (wins are cheaper than losses); the hero can fall only on a
    loss, and is far likelier to if the army is wiped out entirely.
    """
    troops = max(0, troops)
    power = army_power(troops, hero_attack)
    defense = max(1, target.defense)

    win = power * rng.uniform(0.8, 1.2) >= defense
    pressure = defense / max(1, power)            # 1.0 = even fight; >1 = outmatched

    loss_frac = (min(0.60, 0.10 + 0.25 * pressure) if win
                 else min(1.0, 0.45 + 0.40 * pressure))
    troops_lost = min(troops, round(troops * loss_frac))
    survivors = troops - troops_lost

    hero_died = (not win) and rng.random() < (0.60 if survivors == 0 else 0.30)

    loot_gold = target.loot_gold if win else 0
    loot = dict(target.loot) if win else {}

    if win:
        msg = (f"Victory at {target.name}! {survivors}/{troops} soldiers came home "
               f"with {loot_gold} gold.")
    elif hero_died:
        msg = (f"Disaster at {target.name} — the army broke and you fell in "
               f"battle. Only {survivors} made it back.")
    else:
        msg = f"Defeat at {target.name}. {survivors}/{troops} soldiers limped home."

    return RaidResult(
        target=target.name, win=win, troops_sent=troops, survivors=survivors,
        troops_lost=troops_lost, hero_died=hero_died, loot_gold=loot_gold,
        loot=loot, message=msg)
