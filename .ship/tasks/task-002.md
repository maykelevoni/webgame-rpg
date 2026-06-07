# Task 002: Engine — Character, Items, Leveling (pure Python)

## Description
First slice of the pure-Python engine. Define the item shape, the character with
stats/inventory/equip logic, and the leveling math. No Django imports anywhere.

## Files
- `engine/__init__.py` (create — export public classes)
- `engine/items.py` (create)
- `engine/leveling.py` (create)
- `engine/character.py` (create)
- `tests/__init__.py` `tests/test_character.py` `tests/test_leveling.py` (create)

## Requirements
1. `items.py`: `@dataclass Item` with key, name, kind ("consumable"|"weapon"|"armor"),
   price, heal, attack_bonus, defense_bonus. No catalog data here (comes from DB later).
2. `leveling.py`: `xp_to_next(level, xp_base, xp_growth)` and `apply_level_ups(character, stat_growth)`
   that loops while xp ≥ threshold, raising level + stats and carrying surplus.
3. `character.py`: `Character` with name, level, xp, max_hp, hp, base_attack,
   base_defense, gold, inventory (list of (Item, qty)), equipped {slot: Item}.
   Methods: `effective_attack()`, `effective_defense()` (base + equipped bonuses),
   `take_damage(n)`, `heal(n)` (cap at max_hp), `gain_xp(n, cfg)`, `add_item`,
   `remove_item`, `equip(item)`, `unequip(slot)`.
4. Heavy comments aimed at a Python learner. Pure Python — NO Django imports.

## Acceptance Criteria
- [ ] `pytest tests/test_character.py tests/test_leveling.py` passes.
- [ ] Equipping a weapon raises `effective_attack`; healing caps at max_hp.
- [ ] Gaining enough XP increases level and stats, surplus XP carried over.
- [ ] `import engine` works without Django installed/configured.

## Existing Code to Reference
- `.ship/plan.md` Section 3 (engine table)

## Dependencies
- Task 001

## Commit Message
feat(engine): character, items, and leveling core
