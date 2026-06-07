# Task 005: Engine — Plugin loader & Theme registry (pure Python)

## Description
The "modular" core: a plugin registry with hooks, a folder loader, and a theme
discovery helper. Filesystem reads only — still no Django.

## Files
- `engine/plugins.py` (create)
- `engine/themes.py` (create)
- `plugins/__init__.py` (create — empty package)
- `tests/test_plugins.py` (create)

## Requirements
1. `plugins.py`: `PluginRegistry` with extension points:
   `add_monster(monster)`, `add_item(item)`, `add_town_action(name, handler)`, `on_victory(fn)`.
   `load_plugins(plugins_dir, enabled_names)` imports each `*.py` module in the dir
   (skipping names starting with `_` and `__`), and calls its module-level
   `register(registry)` if present and the module name is in `enabled_names`.
2. Registry exposes collected hooks: `.monsters`, `.items`, `.town_actions`, `.victory_hooks`.
3. `themes.py`: `available_themes(themes_dir)` returns sorted folder names that
   contain a `theme.css`.
4. Robust: a broken/missing plugin logs a warning, does not crash the loader.
5. Commented for a learner — this file is the teaching centerpiece of "modular".

## Acceptance Criteria
- [ ] `pytest tests/test_plugins.py` passes (use a temp dir with a fake plugin).
- [ ] Only enabled plugins are loaded; disabled ones are skipped.
- [ ] `register(registry)` hooks land in the registry's collections.
- [ ] `available_themes` lists only folders containing `theme.css`.

## Dependencies
- Task 004

## Commit Message
feat(engine): plugin registry/loader and theme discovery
