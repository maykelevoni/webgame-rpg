"""Items.

An `Item` is just a description of a thing the player can own: a potion, a sword,
a piece of armor. Items have no behaviour of their own beyond their numbers — the
character and combat code decide what those numbers *do*.

The actual list of items in the game (the "catalog") lives in the database and is
editable in the Django admin. The bridge loads those rows and builds `Item`
objects from them, so the engine never has a hardcoded item list.
"""
from dataclasses import dataclass

# The three kinds of item the game understands.
CONSUMABLE = "consumable"  # used up for an effect (e.g. a healing potion)
WEAPON = "weapon"          # equipped, raises attack
ARMOR = "armor"            # equipped, raises defense

GEAR_KINDS = (WEAPON, ARMOR)


@dataclass(frozen=True)
class Item:
    key: str                 # stable id, e.g. "potion" or "iron-sword"
    name: str                # display name, e.g. "Healing Potion"
    kind: str                # one of CONSUMABLE / WEAPON / ARMOR
    price: int = 0           # shop price in gold
    heal: int = 0            # HP restored when used (consumables)
    attack_bonus: int = 0    # added to attack when equipped (weapons)
    defense_bonus: int = 0   # added to defense when equipped (armor)
    icon: str = ""           # sprite name for display (set from the DB), e.g. "tile_0115"
    slot: str = ""           # equipment slot (weapon/shield/helmet/…); "" for non-gear

    @property
    def is_gear(self) -> bool:
        """True for anything with an equipment slot (a thing you wear/wield)."""
        return bool(self.slot)
