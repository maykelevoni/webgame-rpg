# Task 007: Admin registration + data migration seeding

## Description
Make everything manageable in Django admin, and seed starter Items, Monsters, and
the default GameConfig so the game is playable immediately.

## Files
- `game/admin.py` (create)
- `game/migrations/0002_seed_data.py` (create — data migration)

## Requirements
1. `admin.py`: register Character, Item, Monster, InventoryItem, PluginState,
   GameConfig, Profile with useful `list_display` columns (so balancing is easy).
2. Data migration (`RunPython`) seeds:
   - Items: `potion` (consumable, heal 20, price 10), `iron-sword` (weapon, +5 atk, price 40),
     `leather-armor` (armor, +3 def, price 35).
   - Monsters: `goblin` (hp 12, atk 5, def 1, gold 8, xp 12, min_level 1),
     `slime` (hp 8, atk 3, def 0, gold 5, xp 8, min_level 1),
     `wolf` (hp 18, atk 8, def 2, gold 14, xp 20, min_level 2).
   - One `GameConfig` row with plan defaults.
   - Reverse function deletes seeded rows.
3. Idempotent via `update_or_create` on the unique key.

## Acceptance Criteria
- [ ] `migrate` seeds 3 items, 3 monsters, 1 GameConfig.
- [ ] `/admin` shows and lets a superuser edit all models.
- [ ] Migration reverses cleanly.

## Dependencies
- Task 006

## Commit Message
feat(db): admin registration and seed data for items, monsters, config
