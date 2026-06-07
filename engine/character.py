"""The player's character.

This is the heart of the game state: stats, gold, inventory, and equipped gear.
The class holds the *rules* for changing those (take damage, heal, gain XP, equip
an item) but knows nothing about the database or the web — it's plain Python.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from engine.config import EngineConfig
from engine.items import Item
from engine.leveling import apply_level_ups


@dataclass
class InventoryEntry:
    """One stack of an item the character owns.

    ``equipped`` mirrors the database row: a piece of gear can sit in the
    inventory and be equipped at the same time. Consumables are never equipped.
    """
    item: Item
    quantity: int = 1
    equipped: bool = False
    slot: str | None = None


@dataclass
class Character:
    name: str
    level: int = 1
    xp: int = 0
    max_hp: int = 30
    hp: int = 30
    base_attack: int = 8
    base_defense: int = 4
    gold: int = 0
    inventory: list[InventoryEntry] = field(default_factory=list)

    # ----- derived stats -------------------------------------------------
    def _equipped_bonus(self, attr: str) -> int:
        """Sum a bonus (``attack_bonus``/``defense_bonus``) across equipped gear."""
        return sum(getattr(e.item, attr) for e in self.inventory if e.equipped)

    def effective_attack(self) -> int:
        return self.base_attack + self._equipped_bonus("attack_bonus")

    def effective_defense(self) -> int:
        return self.base_defense + self._equipped_bonus("defense_bonus")

    @property
    def is_alive(self) -> bool:
        return self.hp > 0

    # ----- health --------------------------------------------------------
    def take_damage(self, amount: int) -> int:
        """Lose HP (never below 0). Returns the damage actually taken."""
        amount = max(0, amount)
        before = self.hp
        self.hp = max(0, self.hp - amount)
        return before - self.hp

    def heal(self, amount: int) -> int:
        """Restore HP (never above max). Returns the HP actually restored."""
        amount = max(0, amount)
        before = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp - before

    # ----- progression ---------------------------------------------------
    def gain_xp(self, amount: int, cfg: EngineConfig) -> int:
        """Add XP and apply any level-ups. Returns levels gained."""
        self.xp += max(0, amount)
        return apply_level_ups(self, cfg)

    # ----- inventory -----------------------------------------------------
    def find_entry(self, item_key: str) -> InventoryEntry | None:
        for entry in self.inventory:
            if entry.item.key == item_key:
                return entry
        return None

    def add_item(self, item: Item, quantity: int = 1) -> None:
        """Add an item, stacking onto an existing entry when possible."""
        entry = self.find_entry(item.key)
        if entry is not None:
            entry.quantity += quantity
        else:
            self.inventory.append(InventoryEntry(item=item, quantity=quantity))

    def remove_item(self, item_key: str, quantity: int = 1) -> bool:
        """Remove some quantity of an item. Returns True if anything was removed."""
        entry = self.find_entry(item_key)
        if entry is None or entry.quantity < quantity:
            return False
        entry.quantity -= quantity
        if entry.quantity <= 0:
            self.inventory.remove(entry)
        return True

    def use_consumable(self, item_key: str) -> int:
        """Use one consumable for its effect. Returns HP healed (0 if not usable)."""
        entry = self.find_entry(item_key)
        if entry is None or entry.item.kind != "consumable":
            return 0
        healed = self.heal(entry.item.heal)
        self.remove_item(item_key, 1)
        return healed

    # ----- equipment -----------------------------------------------------
    def equip(self, item_key: str) -> bool:
        """Equip a piece of gear, unequipping anything else in the same slot."""
        entry = self.find_entry(item_key)
        if entry is None or not entry.item.is_gear:
            return False
        slot = entry.item.slot
        for other in self.inventory:  # only one item per slot
            if other.equipped and other.slot == slot:
                other.equipped = False
                other.slot = None
        entry.equipped = True
        entry.slot = slot
        return True

    def unequip(self, slot: str) -> bool:
        for entry in self.inventory:
            if entry.equipped and entry.slot == slot:
                entry.equipped = False
                entry.slot = None
                return True
        return False
