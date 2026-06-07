# Task 003: Engine — Monsters & Combat (pure Python)

## Description
Add the monster shape, a spawn-selection helper, and the turn-based combat system.
Combat operates on engine objects only.

## Files
- `engine/monsters.py` (create)
- `engine/combat.py` (create)
- `tests/test_combat.py` (create)

## Requirements
1. `monsters.py`: `@dataclass Monster` (key, name, max_hp, attack, defense,
   gold_reward, xp_reward, min_level). `pick_monster(spawn_list, level, rng)` selects
   a level-appropriate monster from a provided list (DB/plugins supply the list).
2. `combat.py`: `Combat(character, monster, cfg, rng)` with:
   - `player_attack()` → damage = max(1, atk - def); appends to a turn log.
   - `enemy_turn()` → monster hits back.
   - `use_item(item)` → consumable heals, consumes the player's turn.
   - `flee()` → ends combat, outcome="fled".
   - outcome property: "ongoing"/"win"/"lose"/"fled"; on win, `rewards()` returns gold+xp.
3. Deterministic via an injected `rng` (e.g. `random.Random(seed)`) for testability.
4. Pure Python, commented. No Django.

## Acceptance Criteria
- [ ] `pytest tests/test_combat.py` passes.
- [ ] A stronger character defeats a weaker monster → outcome "win" with rewards.
- [ ] Using a potion mid-combat heals and counts as a turn.
- [ ] Fleeing yields outcome "fled" and no rewards.

## Dependencies
- Task 002

## Commit Message
feat(engine): monsters and turn-based combat
