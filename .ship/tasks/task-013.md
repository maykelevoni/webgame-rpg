# Task 013: Example plugin + plugin template

## Description
Prove the modular system end-to-end: ship one working example plugin and a
documented template others can copy.

## Files
- `plugins/healing_shrine.py` (create)
- `plugins/_template_plugin.py.txt` (create)
- `game/migrations/0003_seed_plugin_state.py` (create — register the example plugin enabled)

## Requirements
1. `healing_shrine.py`: module-level `register(registry)` that calls
   `registry.add_town_action("Pray at Shrine", handler)`. The handler heals the
   character for a fixed amount in exchange for a small gold cost. Heavily commented.
2. The town view (Task 012) must render this action only when `PluginState`
   for `healing_shrine` is enabled — disabling it in admin removes the button.
3. Data migration creates a `PluginState(name="healing_shrine", enabled=True)`.
4. `_template_plugin.py.txt`: a fully commented skeleton showing every hook
   (`add_monster`, `add_item`, `add_town_action`, `on_victory`) with TODOs.

## Acceptance Criteria
- [ ] With the plugin enabled, a "Pray at Shrine" button appears in town and heals for gold.
- [ ] Disabling `healing_shrine` in `/admin` removes the button (no code change).
- [ ] The template file documents all hooks.

## Existing Code to Reference
- `engine/plugins.py` (Task 005), `.ship/plan.md` Section 7

## Dependencies
- Task 012

## Commit Message
feat(plugins): healing-shrine example plugin and documented template
