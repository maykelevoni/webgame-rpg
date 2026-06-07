"""Tests for monsters and turn-based combat."""
import random

from engine.character import Character
from engine.combat import Combat, FLED, LOSE, WIN
from engine.config import EngineConfig
from engine.items import Item
from engine.monsters import Monster, pick_monster

CFG = EngineConfig()
POTION = Item(key="potion", name="Potion", kind="consumable", heal=20)


def goblin(**over):
    base = dict(key="goblin", name="Goblin", max_hp=12, attack=5, defense=1,
                gold_reward=8, xp_reward=12, min_level=1)
    base.update(over)
    return Monster(**base)


def test_strong_character_wins_with_rewards():
    hero = Character(name="Hero", base_attack=20, base_defense=10, max_hp=50, hp=50)
    fight = Combat(hero, goblin(), CFG, rng=random.Random(1))
    while not fight.is_over:
        fight.player_attack()
    assert fight.outcome == WIN
    assert fight.rewards() == (8, 12)


def test_weak_character_can_lose():
    hero = Character(name="Hero", base_attack=1, base_defense=0, max_hp=3, hp=3)
    fight = Combat(hero, goblin(max_hp=999, attack=50), CFG)
    fight.player_attack()
    assert fight.outcome == LOSE
    assert fight.rewards() == (0, 0)


def test_using_a_potion_heals_and_costs_a_turn():
    hero = Character(name="Hero", base_attack=5, base_defense=0, max_hp=30, hp=10)
    hero.add_item(POTION, 1)
    fight = Combat(hero, goblin(attack=4, defense=99), CFG)  # monster can't die fast
    fight.use_item("potion")
    # Healed 20 (10 -> 30) then took the monster's 4 damage on its turn.
    assert hero.hp == 26
    assert hero.find_entry("potion") is None  # consumed


def test_flee_ends_without_rewards():
    hero = Character(name="Hero")
    fight = Combat(hero, goblin(), CFG)
    fight.flee()
    assert fight.outcome == FLED
    assert fight.rewards() == (0, 0)


def test_damage_is_never_below_one():
    assert Combat._damage(1, 100) == 1


def test_pick_monster_respects_min_level():
    weak = goblin(key="slime", min_level=1)
    strong = goblin(key="dragon", min_level=10)
    rng = random.Random(0)
    chosen = {pick_monster([weak, strong], level=1, rng=rng).key for _ in range(20)}
    assert chosen == {"slime"}  # never the level-10 monster at level 1
