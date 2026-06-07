"""Example plugin: a Healing Shrine.

This is a complete, working plugin. It adds a "Pray at Shrine" action to the town
menu: for a small gold offering the player recovers some HP. It demonstrates the
whole plugin system in one file:

  * a module-level `register(registry)` function (required), and
  * using a registry hook (`add_town_action`) to add new behaviour.

Try it:
  * The action appears in town while this plugin is enabled.
  * Disable "healing_shrine" in the Django admin (Plugin states) and the button
    disappears — no code change needed.

Copy `_template_plugin.py.txt` to start your own.
"""

# This plugin's own settings. A plugin can hardcode its values since it's an
# optional add-on (the *core* game's balance lives in the database instead).
SHRINE_COST = 5
SHRINE_HEAL = 15


def _pray_at_shrine(character):
    """Handler for the town action. Receives the engine Character; returns a message."""
    if character.gold < SHRINE_COST:
        return "You lack the gold to make an offering at the shrine."
    character.gold -= SHRINE_COST
    healed = character.heal(SHRINE_HEAL)
    return f"You pray and offer {SHRINE_COST} gold. The shrine restores {healed} HP."


def register(registry):
    """Called once at load time. Wire this plugin's features into the game."""
    registry.add_town_action("Pray at Shrine", _pray_at_shrine)
