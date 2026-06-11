"""Tests for the biome map engine — generation, collision, connectivity, pursuit.

Pure Python: the seed and inputs are passed in, so the world is fully reproducible.
"""
from engine import maps as mp
from engine.maps import BiomeMap, MapMonster, biome_spec

SPEC = biome_spec("grass", 12)
SPAWN = [{"key": "slime", "sight_radius": 3, "min_level": 1, "name": "Slime"},
         {"key": "wolf", "sight_radius": 6, "min_level": 2, "name": "Wolf"}]


def gen(seed=1, connections=("c1", "c2"), cleared=None, level=5):
    return BiomeMap.generate(seed, SPEC, cleared=cleared or [],
                             connections=list(connections), spawn_table=SPAWN,
                             player_level=level)


# --- determinism & content -------------------------------------------------
def test_same_seed_same_map():
    a, b = gen(42), gen(42)
    assert a.terrain == b.terrain
    assert [(m.key, m.x, m.y) for m in a.monsters] == [(m.key, m.x, m.y) for m in b.monsters]


def test_counts_and_player_start():
    m = gen(3)
    assert m.player == (m.size // 2, m.size // 2)
    assert len(m.monsters) <= SPEC.monster_count
    assert len(m.chests) <= SPEC.chest_count


def test_min_level_filters_spawns():
    low = gen(3, level=1)               # wolf (min_level 2) ineligible
    assert all(mon.key == "slime" for mon in low.monsters)


# --- collision & connectivity ----------------------------------------------
def test_every_connection_is_reachable():
    m = gen(99, connections=("a", "b", "c"))
    for tile in m.conn_tiles:
        assert m._reachable(m.start, tile), f"{tile} walled off"


def test_water_and_rock_block_movement():
    # Hand-built 3x3: player centre, water to the east, rock to the south.
    terrain = [[mp.GRASS] * 3 for _ in range(3)]
    terrain[1][2] = mp.WATER
    terrain[2][1] = mp.ROCK
    m = BiomeMap(3, terrain, (1, 1), {})
    assert not m.walkable(2, 1) and not m.walkable(1, 2)
    east = m.move("east")
    assert east.kind == mp.BLOCKED and m.player == (1, 1)
    south = m.move("south")
    assert south.kind == mp.BLOCKED and m.player == (1, 1)
    north = m.move("north")
    assert north.kind == mp.MOVED and m.player == (1, 0)


def test_stepping_on_features():
    terrain = [[mp.GRASS] * 3 for _ in range(3)]
    m = BiomeMap(3, terrain, (1, 1), {(2, 1): "exit42"})
    m.resources[(1, 0)] = "wood"
    m.chests.add((0, 1))
    assert m.move("east").kind == mp.CONNECTION
    m.player_x, m.player_y = 1, 1
    north = m.move("north")
    assert north.kind == mp.RESOURCE and north.data == "wood"
    m.player_x, m.player_y = 1, 1
    assert m.move("west").kind == mp.CHEST


# --- monster aggro (stationary; engage when the player steps adjacent) ------
def test_monsters_do_not_move():
    terrain = [[mp.GRASS] * 7 for _ in range(7)]
    m = BiomeMap(7, terrain, (0, 0), {})
    m.player_x, m.player_y = 6, 6
    mon = MapMonster("wolf", x=3, y=3, sx=3, sy=3)
    m.monsters = [mon]
    m.aggro_check()
    assert (mon.x, mon.y) == (3, 3)         # it holds its ground, never pursues


def test_adjacent_monster_engages():
    terrain = [[mp.GRASS] * 3 for _ in range(3)]
    m = BiomeMap(3, terrain, (1, 1), {})
    mon = MapMonster("slime", x=2, y=1, sx=2, sy=1)   # orthogonally adjacent
    m.monsters = [mon]
    assert m.aggro_check() is mon


def test_diagonally_adjacent_monster_engages():
    terrain = [[mp.GRASS] * 3 for _ in range(3)]
    m = BiomeMap(3, terrain, (1, 1), {})
    mon = MapMonster("slime", x=2, y=2, sx=2, sy=2)   # diagonal counts as close
    m.monsters = [mon]
    assert m.aggro_check() is mon


def test_distant_monster_does_not_engage():
    terrain = [[mp.GRASS] * 7 for _ in range(7)]
    m = BiomeMap(7, terrain, (0, 0), {})
    mon = MapMonster("wolf", x=3, y=3, sx=3, sy=3)     # two+ tiles away
    m.monsters = [mon]
    assert m.aggro_check() is None


# --- settlement (walk your village, Phase 2a) ------------------------------
def settlement(size=6):
    # A 2x2 Longhouse centred, a 1x1 Market beside it.
    return BiomeMap.settlement(size, [
        ("longhouse", 2, 2, 2, 2),
        ("market", 1, 1, 1, 1),
    ], gate_conn_id="back")


def test_settlement_footprints_are_solid():
    m = settlement()
    for tile in [(2, 2), (3, 2), (2, 3), (3, 3), (1, 1)]:
        assert tile in m.buildings
        assert not m.walkable(*tile)       # buildings block movement


def test_bumping_a_building_returns_its_key():
    m = settlement()
    m.player_x, m.player_y = 2, 1          # standing just north of the Longhouse
    res = m.move("south")
    assert res.kind == mp.BUILDING and res.data == "longhouse"
    assert m.player == (2, 1)              # you don't step onto it


def test_settlement_gate_is_walkable_and_entry_adjacent():
    m = settlement()
    gate = next(t for t, cid in m.conn_tiles.items() if cid == "back")
    assert gate[1] == m.size - 1           # gate sits on the bottom edge
    assert gate not in m.buildings         # and is walkable
    # the player spawns adjacent to the gate, so the exit is reachable
    assert abs(m.player[0] - gate[0]) + abs(m.player[1] - gate[1]) == 1


def test_settlement_gate_returns_connection():
    m = settlement()
    gate = next(t for t, cid in m.conn_tiles.items() if cid == "back")
    m.player_x, m.player_y = gate[0], gate[1] - 1   # the entry, just above the gate
    res = m.move("south")
    assert res.kind == mp.CONNECTION and res.data == "back"


# --- edge exit: walking off the grid returns to the World Map ---------------
def test_walking_off_the_edge_returns_edge_exit():
    m = gen(7)
    # Put the player on the left column on a walkable tile, then step west (off-grid).
    y = next(yy for yy in range(m.size) if m.walkable(0, yy))
    m.player_x, m.player_y = 0, y
    res = m.move("west")
    assert res.kind == mp.EDGE_EXIT
    assert m.player == (0, y)            # you don't move onto the off-grid tile


def test_blocked_terrain_is_not_an_edge_exit():
    m = gen(7)
    # An in-bounds blocker (water/rock) stays BLOCKED, not EDGE_EXIT.
    blocker = next(((x, yy) for yy in range(m.size) for x in range(m.size)
                    if m.in_bounds(x, yy) and not m.walkable(x, yy)), None)
    if blocker is None:
        return                            # no blockers this seed; nothing to assert
    bx, by = blocker
    # stand next to it and step into it
    for d, (dx, dy) in {"east": (-1, 0), "west": (1, 0),
                        "south": (0, -1), "north": (0, 1)}.items():
        px, py = bx + dx, by + dy
        if m.in_bounds(px, py) and m.walkable(px, py):
            m.player_x, m.player_y = px, py
            assert m.move(d).kind == mp.BLOCKED
            break
