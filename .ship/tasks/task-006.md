# Task 006: Django models + migrations

## Description
Define all persistence models on Neon: Profile, Character, Item, Monster,
InventoryItem, PluginState, GameConfig. Generate migrations.

## Files
- `game/models.py` (create)
- `game/migrations/__init__.py` (create)

## Requirements
1. Implement models exactly per `.ship/plan.md` Section 2:
   - `Profile(user OneToOne, theme default "dark-fantasy")`
   - `Character(owner FK User, name, level, xp, max_hp, hp, base_attack, base_defense,
     gold, map_seed, pos_x, pos_y, cleared JSONField default list, created/updated)`
   - `Item(key Slug unique, name, kind choices, price, heal, attack_bonus, defense_bonus, sellable)`
   - `Monster(key Slug unique, name, max_hp, attack, defense, gold_reward, xp_reward, min_level)`
   - `InventoryItem(character FK, item FK, quantity, equipped, slot)`
   - `PluginState(name unique, enabled)`
   - `GameConfig` singleton with all balance fields + a `load()` classmethod returning
     the single row (pk=1, get_or_create with defaults) and a `save()` that forces pk=1.
2. Sensible `__str__` and choices. `cleared` stored as list of [x,y].
3. `python manage.py makemigrations game` produces a clean migration.

## Acceptance Criteria
- [ ] `makemigrations` + `migrate` run clean against Neon.
- [ ] `GameConfig.load()` returns/creates the single config row.
- [ ] All models importable; `manage.py check` passes.

## Dependencies
- Task 001

## Commit Message
feat(db): models for character, items, monsters, plugins, and game config
