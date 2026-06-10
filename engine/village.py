"""The village: a base the player builds, on its own grid.

Unlike the overworld (which is regenerated from a seed every load), the village
layout is *authored by the player and saved*. This module holds the pure-Python
rules: building costs, build timers, resource production, and the "catch up on the
time that passed while you were away" calculation.

Like the rest of ``engine/`` there is no Django, no database, and no clock of its
own — the current time is always *passed in* (``now``, unix seconds), so every
function here is deterministic and unit-testable. The bridge
(``game/services.py``) supplies the real clock and turns DB rows into the
``BuildingDef`` / ``VillageState`` objects below.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from engine.army import UPKEEP_MEAT_PER_MIN

# --- resources -------------------------------------------------------------
WOOD = "wood"
STONE = "stone"
MEAT = "meat"
IRON = "iron"            # mined at the Village, spent at the Castle Smithy to refine gear
RESOURCES = (WOOD, STONE, MEAT, IRON)

# The Longhouse is the special building whose level is your rank and gates
# everything else (you can't build higher than your Longhouse).
LONGHOUSE = "longhouse"

# Tuning constants. Kept here for slice 1; can move to GameConfig (admin) later.
BASE_STORAGE = 500        # starting resource cap before any Storehouse
GRID_BASE = 6             # village grid side at Longhouse level 1
GRID_CAP = 14             # grid never grows past this

# Rank titles by Longhouse level — the "become a King" progression spine.
RANKS = [(1, "Outcast"), (3, "Karl"), (5, "Hersir"), (8, "Jarl"), (10, "King")]


def rank_title(longhouse_level: int) -> str:
    """Map a Longhouse level to its Viking title."""
    title = RANKS[0][1]
    for lvl, name in RANKS:
        if longhouse_level >= lvl:
            title = name
    return title


def grid_size_for(longhouse_level: int) -> int:
    """The buildable grid grows by one tile per Longhouse level (capped)."""
    return min(GRID_BASE + max(0, longhouse_level - 1), GRID_CAP)


# --- the catalog (one per building type, loaded from the DB) ---------------
@dataclass
class BuildingDef:
    """The rules for one *type* of building. Costs/times/rates are balance knobs."""
    key: str
    name: str
    category: str = "production"   # production / storage / progression / military / defense
    footprint_w: int = 1
    footprint_h: int = 1
    cost_wood: int = 0
    cost_stone: int = 0
    cost_growth: float = 1.6       # cost multiplier per level
    build_seconds: int = 5
    build_growth: float = 1.7      # build-time multiplier per level
    produces: str = ""             # one of RESOURCES, or "" for none
    production_rate: int = 0       # units per MINUTE at level 1
    storage_bonus: int = 0         # added to the resource cap, per level
    max_level: int = 5
    requires_longhouse_level: int = 1
    # How many of this building you may own, by Longhouse level. Keys are the
    # Longhouse level at which a new slot unlocks; the cap is the value at the
    # highest unlocked level. e.g. {1: 1, 3: 2, 5: 3} -> 1 at LH1, 2 at LH3, 3 at LH5.
    max_counts: dict = field(default_factory=dict)
    icon: str = ""
    emoji: str = ""

    def allowed_count(self, longhouse_level: int) -> int:
        """How many of this building are permitted at the given Longhouse level."""
        unlocked = [(int(k), v) for k, v in self.max_counts.items()
                    if int(k) <= longhouse_level]
        return max(unlocked, key=lambda kv: kv[0])[1] if unlocked else 0

    def cost(self, target_level: int) -> dict[str, int]:
        """Resource cost to reach ``target_level`` (1 = the first build)."""
        mult = self.cost_growth ** (target_level - 1)
        return {WOOD: int(self.cost_wood * mult), STONE: int(self.cost_stone * mult)}

    def build_time(self, target_level: int) -> int:
        """Seconds to build/upgrade to ``target_level``."""
        return int(self.build_seconds * (self.build_growth ** (target_level - 1)))

    def rate_at(self, level: int) -> int:
        """Production per minute at a completed ``level`` (linear)."""
        return self.production_rate * level

    def storage_at(self, level: int) -> int:
        return self.storage_bonus * level


# --- a building the player has placed --------------------------------------
@dataclass
class PlacedBuilding:
    """One building standing (or being built) in the village.

    ``level`` is the *completed* level. While ``build_finish`` is set the building
    is working toward ``level + 1`` (a fresh placement starts at level 0 and
    completes to 1). Production only counts the completed level.
    """
    key: str
    level: int = 0
    x: int = 0
    y: int = 0
    build_finish: float | None = None   # unix ts the current build completes; None = idle
    id: int | None = None               # DB id, set by the bridge (for upgrades)

    def is_building(self, now: float) -> bool:
        return self.build_finish is not None and now < self.build_finish

    def target_level(self) -> int:
        return self.level + 1


# --- the whole village state ----------------------------------------------
@dataclass
class VillageState:
    wood: int = 0
    stone: int = 0
    meat: int = 0
    iron: int = 0
    troops: int = 0                 # trained warriors (the warband for raids)
    last_tick: float = 0.0
    buildings: list[PlacedBuilding] = field(default_factory=list)

    # resource access by name (keeps the tick/cap code tidy)
    def get(self, res: str) -> int:
        return getattr(self, res)

    def set(self, res: str, amount: int) -> None:
        setattr(self, res, max(0, int(amount)))

    def add(self, res: str, amount: int) -> None:
        self.set(res, self.get(res) + amount)


# --- queries over the state ------------------------------------------------
def find_longhouse(state: VillageState) -> PlacedBuilding | None:
    for b in state.buildings:
        if b.key == LONGHOUSE:
            return b
    return None


def longhouse_level(state: VillageState) -> int:
    """Current rank level — the completed Longhouse level (1 if none yet)."""
    lh = find_longhouse(state)
    return lh.level if lh and lh.level > 0 else 1


def count_of(state: VillageState, key: str) -> int:
    """How many of a building type are placed (built or under construction)."""
    return sum(1 for b in state.buildings if b.key == key)


def occupied_tiles(state: VillageState, defs: dict[str, BuildingDef]) -> set[tuple[int, int]]:
    """Every grid tile currently covered by a building footprint."""
    taken: set[tuple[int, int]] = set()
    for b in state.buildings:
        d = defs.get(b.key)
        if not d:
            continue
        for dx in range(d.footprint_w):
            for dy in range(d.footprint_h):
                taken.add((b.x + dx, b.y + dy))
    return taken


def can_place(state: VillageState, defs: dict[str, BuildingDef], bdef: BuildingDef,
              x: int, y: int) -> tuple[bool, str]:
    """Can ``bdef`` be placed with its top-left corner at (x, y)?  -> (ok, reason)."""
    size = grid_size_for(longhouse_level(state))
    if x < 0 or y < 0 or x + bdef.footprint_w > size or y + bdef.footprint_h > size:
        return False, "It doesn't fit inside the village."
    taken = occupied_tiles(state, defs)
    for dx in range(bdef.footprint_w):
        for dy in range(bdef.footprint_h):
            if (x + dx, y + dy) in taken:
                return False, "Those tiles are already occupied."
    lh = longhouse_level(state)
    if lh < bdef.requires_longhouse_level:
        return False, f"Requires Longhouse level {bdef.requires_longhouse_level}."
    allowed = bdef.allowed_count(lh)
    if count_of(state, bdef.key) >= allowed:
        return False, (f"You can only have {allowed} {bdef.name} at Longhouse "
                       f"Lv {lh} — upgrade your Longhouse for more.")
    return True, ""


def can_afford(state: VillageState, cost: dict[str, int]) -> bool:
    return all(state.get(res) >= amount for res, amount in cost.items())


def storage_cap(state: VillageState, defs: dict[str, BuildingDef]) -> int:
    """Max amount of any single resource the village can hold."""
    cap = BASE_STORAGE
    for b in state.buildings:
        d = defs.get(b.key)
        if d and d.storage_bonus and b.level > 0:
            cap += d.storage_at(b.level)
    return cap


def production_rates(state: VillageState, defs: dict[str, BuildingDef]) -> dict[str, int]:
    """Units produced per minute, per resource, at current completed levels."""
    rates = {r: 0 for r in RESOURCES}
    for b in state.buildings:
        d = defs.get(b.key)
        if d and d.produces and b.level > 0:
            rates[d.produces] += d.rate_at(b.level)
    return rates


def troop_upkeep_per_min(state: VillageState) -> float:
    """Meat the warband eats per minute."""
    return UPKEEP_MEAT_PER_MIN * max(0, state.troops)


def food_balance(state: VillageState, defs: dict[str, BuildingDef]) -> int:
    """Net meat per minute: production minus the warband's food upkeep. If this is
    negative the village is starving and troops will desert over time."""
    return int(production_rates(state, defs)[MEAT] - troop_upkeep_per_min(state))


# --- the one mechanic that happens on its own over time --------------------
def tick(state: VillageState, defs: dict[str, BuildingDef], now: float) -> list[str]:
    """Advance the village to ``now``: accrue offline production (capped) and
    finish any builds whose timer elapsed. Mutates ``state``; returns a list of
    human-readable "while you were away…" events. Idempotent given the same ``now``.
    """
    events: list[str] = []
    elapsed = max(0.0, now - state.last_tick)

    # 1) Accrue production at the levels that were completed during the window.
    if elapsed > 0:
        minutes = elapsed / 60.0
        cap = storage_cap(state, defs)
        for res, rate in production_rates(state, defs).items():
            if rate <= 0:
                continue
            before = state.get(res)
            after = min(cap, before + int(rate * minutes))
            if after > before:
                state.set(res, after)

    # 1b) Feed the warband. Each warrior eats meat every minute; if the stores run
    #     out the unfed warriors desert (they leave — they don't drop dead), and the
    #     meat floors at zero. Gentle, time-based: it punishes idle army-spam.
    if state.troops > 0 and elapsed > 0:
        minutes = elapsed / 60.0
        need = troop_upkeep_per_min(state) * minutes      # meat the warband wants
        have = state.get(MEAT)
        if need <= have:
            state.set(MEAT, have - int(round(need)))
        else:
            per_troop = max(1e-6, UPKEEP_MEAT_PER_MIN * minutes)
            deserters = min(state.troops, math.ceil((need - have) / per_troop))
            state.set(MEAT, 0)
            if deserters > 0:
                state.troops -= deserters
                events.append(
                    f"{deserters} warrior{'s' if deserters != 1 else ''} deserted — "
                    f"no meat to feed them.")

    # 2) Complete any finished builds (a building can only run one job at a time).
    for b in state.buildings:
        if b.build_finish is not None and now >= b.build_finish:
            b.level += 1
            b.build_finish = None
            d = defs.get(b.key)
            name = d.name if d else b.key
            events.append(f"{name} finished (Lv {b.level}).")

    state.last_tick = now
    return events
