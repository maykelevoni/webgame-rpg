"""webgame-rpg game engine — pure Python, no Django.

Importing from here gives you the public game objects without reaching into
individual modules. The golden rule: nothing in this package imports Django.
"""
from engine.character import Character, InventoryEntry
from engine.config import EngineConfig
from engine.items import ARMOR, CONSUMABLE, WEAPON, Item
from engine.leveling import apply_level_ups, xp_to_next

__all__ = [
    "Character",
    "InventoryEntry",
    "EngineConfig",
    "Item",
    "CONSUMABLE",
    "WEAPON",
    "ARMOR",
    "apply_level_ups",
    "xp_to_next",
]
