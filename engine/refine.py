"""Gear refinement — the Castle Smithy's upgrade mechanic.

Pure Python (no Django, RNG passed in). A piece of gear has a *refine level* that
adds to the stat it already grants (a +3 sword hits for its base attack + 3). You
spend **iron + gold** to attempt the next level:

- Levels up to ``SAFE_LEVEL`` (+3) **always succeed**.
- Above that, success gets harder and a **failure knocks the item down one level**
  (MU-style), so pushing a high refine is a real gamble. Materials are always spent.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

MAX_LEVEL = 9        # the highest a piece of gear can be refined to
SAFE_LEVEL = 3       # refines up to (and including) this never fail


def cost(target_level: int) -> tuple[int, int]:
    """(iron, gold) to attempt a refine to ``target_level`` (1 = the first +1)."""
    return (3 * target_level, 10 * target_level)


def success_chance(target_level: int) -> float:
    """Odds the attempt to reach ``target_level`` succeeds (1.0 at/under SAFE_LEVEL)."""
    if target_level <= SAFE_LEVEL:
        return 1.0
    return max(0.30, 1.0 - 0.15 * (target_level - SAFE_LEVEL))


@dataclass
class RefineResult:
    affordable: bool          # could the costs be paid (the attempt happened)?
    success: bool             # did it reach the next level?
    old_level: int
    new_level: int
    iron_cost: int
    gold_cost: int
    at_max: bool = False      # already at MAX_LEVEL (no attempt)
    message: str = ""


def attempt(level: int, iron: int, gold: int,
            rng: random.Random | None = None) -> RefineResult:
    """Try to refine a piece of gear currently at ``level`` to ``level + 1``.

    Materials are only checked/spent when an attempt is actually possible. On a
    failed attempt above ``SAFE_LEVEL`` the item drops one level (never below 0).
    """
    rng = rng or random.Random()
    target = level + 1
    if level >= MAX_LEVEL:
        return RefineResult(False, False, level, level, 0, 0, at_max=True,
                            message=f"Already refined to the maximum (+{MAX_LEVEL}).")
    iron_cost, gold_cost = cost(target)
    if iron < iron_cost or gold < gold_cost:
        return RefineResult(False, False, level, level, iron_cost, gold_cost,
                            message=f"Need {iron_cost} iron and {gold_cost} gold.")

    if rng.random() < success_chance(target):
        return RefineResult(True, True, level, target, iron_cost, gold_cost,
                            message=f"Success! Refined to +{target}.")
    # Failure: safe levels can't reach here, so this is always above SAFE_LEVEL.
    new_level = max(0, level - 1)
    return RefineResult(True, False, level, new_level, iron_cost, gold_cost,
                        message=f"The refine failed — the gear dropped to +{new_level}.")
