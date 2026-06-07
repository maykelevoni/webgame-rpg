"""Tests for the world grid and movement."""
from engine.config import EngineConfig
from engine.world import (
    BLOCKED, MONSTER, MOVED, TOWN, TREASURE, World,
)

CFG = EngineConfig(grid_size=10, monster_count=6, treasure_count=3)


def test_same_seed_makes_the_same_map():
    a = World.generate(seed=42, cfg=CFG)
    b = World.generate(seed=42, cfg=CFG)
    assert a.town == b.town
    assert a.monsters == b.monsters
    assert a.treasures == b.treasures


def test_map_has_expected_counts():
    w = World.generate(seed=7, cfg=CFG)
    assert len([w.town]) == 1
    assert len(w.monsters) == CFG.monster_count
    assert len(w.treasures) == CFG.treasure_count
    # Nothing overlaps the player's start tile.
    assert w.player not in w.monsters
    assert w.player not in w.treasures


def test_cleared_tiles_are_not_repopulated():
    w0 = World.generate(seed=7, cfg=CFG)
    a_monster = next(iter(w0.monsters))
    w1 = World.generate(seed=7, cfg=CFG, cleared=[list(a_monster)])
    assert a_monster not in w1.monsters
    assert len(w1.monsters) == CFG.monster_count - 1


def test_moving_off_the_edge_is_blocked():
    w = World(size=10, town=(0, 0), monsters=set(), treasures=set(), player=(0, 5))
    result = w.move("west")  # x would become -1
    assert result.kind == BLOCKED
    assert w.player == (0, 5)  # position unchanged


def test_stepping_onto_entities_reports_them():
    w = World(size=10, town=(2, 1), monsters={(2, 0)}, treasures={(1, 1)}, player=(1, 0))
    # move east onto the monster at (2,0)
    assert w.move("east").kind == MONSTER
    # now at (2,0); move south onto the town at (2,1)
    assert w.move("south").kind == TOWN


def test_plain_move_reports_moved():
    w = World(size=10, town=(9, 9), monsters=set(), treasures=set(), player=(5, 5))
    assert w.move("north").kind == MOVED
    assert w.player == (5, 4)
