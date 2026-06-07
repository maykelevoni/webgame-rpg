"""The plugin system — how the game is made modular.

A *plugin* is just a Python file in the ``plugins/`` folder that defines a
top-level ``register(registry)`` function. When the game starts it scans that
folder, imports each enabled plugin, and calls its ``register`` with a shared
`PluginRegistry`. The plugin uses the registry to add content or behaviour:

    def register(registry):
        registry.add_town_action("Pray at Shrine", my_handler)

The core game (world, combat, inventory) is *not* a plugin — plugins only add to
it through the hooks below. This keeps the foundation stable while leaving the
fun, experimental stuff to drop-in files.
"""
from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from typing import Callable, Iterable

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Collects everything plugins contribute. The app reads these afterwards."""

    def __init__(self):
        self.monsters: list = []                       # extra monsters to spawn
        self.items: list = []                          # extra catalog items
        self.town_actions: dict[str, Callable] = {}    # label -> handler(character)
        self.victory_hooks: list[Callable] = []        # called after each win

    # --- hooks a plugin calls inside register() ---
    def add_monster(self, monster) -> None:
        self.monsters.append(monster)

    def add_item(self, item) -> None:
        self.items.append(item)

    def add_town_action(self, label: str, handler: Callable) -> None:
        self.town_actions[label] = handler

    def on_victory(self, fn: Callable) -> None:
        self.victory_hooks.append(fn)

    # --- used by the rest of the app ---
    def run_victory_hooks(self, character) -> None:
        for fn in self.victory_hooks:
            try:
                fn(character)
            except Exception:  # one bad plugin shouldn't break a fight
                logger.exception("victory hook failed")


def load_plugins(
    plugins_dir: str | Path,
    enabled_names: Iterable[str] | None = None,
) -> PluginRegistry:
    """Import every enabled plugin in ``plugins_dir`` and collect its hooks.

    ``enabled_names`` is the set of plugin module names that are turned on
    (from the database). Pass ``None`` to load all of them. Files starting with
    ``_`` (like the template) are always skipped. A broken plugin is logged and
    skipped rather than crashing the game.
    """
    registry = PluginRegistry()
    base = Path(plugins_dir)
    if not base.is_dir():
        return registry

    enabled = set(enabled_names) if enabled_names is not None else None

    for file in sorted(base.glob("*.py")):
        name = file.stem
        if name.startswith("_"):  # __init__.py, _template_plugin, etc.
            continue
        if enabled is not None and name not in enabled:
            continue
        try:
            spec = importlib.util.spec_from_file_location(f"ezrpg_plugin_{name}", file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            register = getattr(module, "register", None)
            if callable(register):
                register(registry)
            else:
                logger.warning("plugin %s has no register() function", name)
        except Exception:
            logger.exception("failed to load plugin %s", name)

    return registry
