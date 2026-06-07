# Task 008: Bridge services + identity seam

## Description
The single layer that maps DB rows ↔ engine objects. Views will only call these.
This is where DB access lives; the engine stays pure.

## Files
- `game/identity.py` (create)
- `game/services.py` (create)

## Requirements
1. `identity.py`: `get_current_player(request)` → returns the request user's
   `Character` model (or None). The only seam between auth and the game.
2. `services.py` functions per `.ship/plan.md` Section 4:
   - `load_config()` → engine config object from `GameConfig.load()`.
   - `load_catalog()` → `{key: engine Item}` from `Item` rows.
   - `load_spawn_table(enabled_plugins)` → list of engine `Monster` from `Monster`
     rows plus plugin-added monsters.
   - `get_or_create_character(user, name=None)` → build engine `Character` from the
     `Character` model + `InventoryItem` rows (items resolved via catalog).
   - `save_character(engine_char, model)` → persist stats, gold, xp, level, hp,
     position, cleared, and rewrite inventory/equipped rows.
   - `load_world(character_model)` → engine `World` from seed + cleared + config + spawn table.
   - `do_move`, `start_combat`, `combat_action`, `buy_item`, `sell_item`,
     `equip_item`, `use_item`, `rest` — orchestrate engine + persist.
   - `get_active_plugins()` → `PluginRegistry` from enabled `PluginState` + `load_plugins`.
3. Engine receives only plain objects — never querysets. Commented.

## Acceptance Criteria
- [ ] Round-trip: create character → save → reload gives identical state.
- [ ] `load_catalog`/`load_spawn_table` return engine objects, not models.
- [ ] No engine module imports anything from `game/` or `django`.

## Dependencies
- Task 005, Task 007

## Commit Message
feat(game): bridge services mapping DB to engine, plus identity seam
