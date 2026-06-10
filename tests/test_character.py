"""Tests for the Character — stats, health, inventory, equipment."""
from engine.character import Character
from engine.items import Item


POTION = Item(key="potion", name="Potion", kind="consumable", price=10, heal=20)
SWORD = Item(key="sword", name="Sword", kind="weapon", price=40, attack_bonus=5, slot="weapon")
ARMOR = Item(key="armor", name="Armor", kind="armor", price=35, defense_bonus=3, slot="armor")


def test_effective_stats_include_equipped_gear():
    c = Character(name="Hero", base_attack=8, base_defense=4)
    c.add_item(SWORD)
    c.add_item(ARMOR)
    assert c.effective_attack() == 8       # not equipped yet
    c.equip("sword")
    c.equip("armor")
    assert c.effective_attack() == 13       # 8 + 5
    assert c.effective_defense() == 7       # 4 + 3


def test_take_damage_and_heal_are_clamped():
    c = Character(name="Hero", max_hp=30, hp=30)
    assert c.take_damage(100) == 30        # cannot go below 0
    assert c.hp == 0
    assert not c.is_alive
    assert c.heal(1000) == 30              # cannot exceed max
    assert c.hp == 30


def test_inventory_stacks_and_removes():
    c = Character(name="Hero")
    c.add_item(POTION, 2)
    c.add_item(POTION, 1)
    assert c.find_entry("potion").quantity == 3
    assert c.remove_item("potion", 2) is True
    assert c.find_entry("potion").quantity == 1
    assert c.remove_item("potion", 5) is False   # not enough to remove


def test_use_consumable_heals_and_consumes():
    c = Character(name="Hero", max_hp=30, hp=10)
    c.add_item(POTION, 1)
    healed = c.use_consumable("potion")
    assert healed == 20
    assert c.hp == 30
    assert c.find_entry("potion") is None        # used up


def test_equipping_same_slot_swaps():
    big = Item(key="great-sword", name="Great Sword", kind="weapon", attack_bonus=9, slot="weapon")
    c = Character(name="Hero", base_attack=8)
    c.add_item(SWORD)
    c.add_item(big)
    c.equip("sword")
    c.equip("great-sword")                        # same slot -> swaps
    assert c.effective_attack() == 17             # 8 + 9 only
    equipped = [e.item.key for e in c.inventory if e.equipped]
    assert equipped == ["great-sword"]
