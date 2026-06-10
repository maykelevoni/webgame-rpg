"""Biome maps — the explorable world.

An evolution of ``world.py``: instead of one bare grid, each *area* is a biome map
generated from a seed, with **real terrain you navigate around** (water and rock are
impassable), **visible content** (resource nodes, chests, monsters), and **fixed
connections** out to other areas. Monsters are entities with positions that **hunt
the player** — within their sight radius they step toward you each turn and fight on
contact.

Pure Python, like the rest of ``engine/``: the current time, the random seed, the
list of already-cleared tiles, and the spawn/connection tables are all *passed in*.
The bridge (``game/services.py``) turns DB rows into the plain inputs below and the
results back into sprites and saved state.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

# --- terrain ---------------------------------------------------------------
GRASS = "grass"      # walkable floor (theme/biome decides the sprite)
WATER = "water"      # impassable — walk around it
ROCK = "rock"        # impassable — walls / boulders
BLOCKERS = {WATER, ROCK}

# Monsters hold their ground (no pursuit). They pounce — start a fight — when the
# player ends a move within this many tiles (Chebyshev) of them.
ENGAGE_RANGE = 1

# --- move / step outcomes --------------------------------------------------
MOVED = "moved"
BLOCKED = "blocked"
MONSTER = "monster"        # bumped a monster -> fight
CHEST = "chest"
RESOURCE = "resource"
CONNECTION = "connection"  # stepped on an exit -> change area
BUILDING = "building"      # bumped a settlement building -> use it (don't step on)


@dataclass
class MoveResult:
    kind: str
    x: int = 0
    y: int = 0
    data: object = None     # the monster / conn_id / resource type, by kind


@dataclass
class MapMonster:
    """A monster standing on the map. Combat stats are looked up from the template
    by ``key`` at fight time; we only need movement info here."""
    key: str
    x: int
    y: int
    sx: int                 # spawn tile (so a defeat can be remembered in `cleared`)
    sy: int
    sight_radius: int = 4
    name: str = ""
    icon: str = ""


# --- biome generation rules (admin-independent tuning lives here for slice 1) --
@dataclass
class BiomeSpec:
    biome: str
    size: int
    water: float = 0.07         # share of tiles that are water
    rock: float = 0.07          # share that are rock
    monster_count: int = 5
    chest_count: int = 2
    resource_count: int = 4
    resources: tuple[str, ...] = ("wood", "meat")


BIOMES = {
    "grass":   dict(water=0.07, rock=0.07, monster_count=5, chest_count=2,
                    resource_count=5, resources=("wood", "meat")),
    "dungeon": dict(water=0.0, rock=0.22, monster_count=7, chest_count=3,
                    resource_count=3, resources=("stone",)),
    "desert":  dict(water=0.02, rock=0.12, monster_count=5, chest_count=2,
                    resource_count=4, resources=("stone",)),
    "ice":     dict(water=0.14, rock=0.06, monster_count=5, chest_count=2,
                    resource_count=4, resources=("stone", "meat")),
}


def biome_spec(biome: str, size: int) -> BiomeSpec:
    rules = BIOMES.get(biome, BIOMES["grass"])
    return BiomeSpec(biome=biome, size=size, **rules)


class BiomeMap:
    def __init__(self, size: int, terrain: list[list[str]],
                 start: tuple[int, int], conn_tiles: dict[tuple[int, int], str]):
        self.size = size
        self.terrain = terrain                 # terrain[y][x]
        self.start = start
        self.player_x, self.player_y = start
        self.conn_tiles = conn_tiles           # (x,y) -> connection id
        self.resources: dict[tuple[int, int], str] = {}
        self.chests: set[tuple[int, int]] = set()
        self.monsters: list[MapMonster] = []
        self.buildings: dict[tuple[int, int], str] = {}  # (x,y) -> building key (settlement)

    # ----- queries -------------------------------------------------------
    @property
    def player(self) -> tuple[int, int]:
        return (self.player_x, self.player_y)

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.size and 0 <= y < self.size

    def walkable(self, x: int, y: int) -> bool:
        return (self.in_bounds(x, y) and self.terrain[y][x] not in BLOCKERS
                and (x, y) not in self.buildings)

    def monster_at(self, x: int, y: int) -> MapMonster | None:
        for m in self.monsters:
            if (m.x, m.y) == (x, y):
                return m
        return None

    # ----- construction --------------------------------------------------
    @classmethod
    def generate(cls, seed: int, spec: BiomeSpec, cleared: list | None = None,
                 connections: list[str] | None = None,
                 spawn_table: list[dict] | None = None,
                 player_level: int = 1) -> "BiomeMap":
        rng = random.Random(seed)
        size = spec.size
        cleared_set = {tuple(c) for c in (cleared or [])}
        connections = connections or []
        spawn_table = spawn_table or []

        terrain = [[GRASS] * size for _ in range(size)]
        for _ in range(int(size * size * spec.water)):
            terrain[rng.randrange(size)][rng.randrange(size)] = WATER
        for _ in range(int(size * size * spec.rock)):
            terrain[rng.randrange(size)][rng.randrange(size)] = ROCK

        start = (size // 2, size // 2)
        terrain[start[1]][start[0]] = GRASS

        # Connections sit on the edges; keep their tiles clear.
        edges = [(size // 2, 0), (size // 2, size - 1), (0, size // 2),
                 (size - 1, size // 2), (0, 0), (size - 1, size - 1)]
        conn_tiles: dict[tuple[int, int], str] = {}
        for i, cid in enumerate(connections):
            tx, ty = edges[i % len(edges)]
            terrain[ty][tx] = GRASS
            conn_tiles[(tx, ty)] = cid

        m = cls(size, terrain, start, conn_tiles)

        # Guarantee you can actually reach every exit: carve a corridor to any
        # connection the random terrain happened to wall off.
        for tile in conn_tiles:
            if not m._reachable(start, tile):
                m._carve(start, tile)

        # Content goes only on reachable, free, not-yet-cleared tiles.
        reserved = set(conn_tiles) | {start}
        free = [t for t in m._reachable_tiles(start)
                if t not in reserved and t not in cleared_set]
        rng.shuffle(free)

        for _ in range(spec.resource_count):
            if not free:
                break
            x, y = free.pop()
            m.resources[(x, y)] = rng.choice(spec.resources) if spec.resources else "wood"
        for _ in range(spec.chest_count):
            if not free:
                break
            m.chests.add(free.pop())

        eligible = [t for t in spawn_table if t.get("min_level", 1) <= player_level] or spawn_table
        for _ in range(spec.monster_count):
            if not free or not eligible:
                break
            x, y = free.pop()
            t = rng.choice(eligible)
            m.monsters.append(MapMonster(
                key=t["key"], x=x, y=y, sx=x, sy=y,
                sight_radius=t.get("sight_radius", 4),
                name=t.get("name", ""), icon=t.get("icon", "")))
        return m

    # ----- connectivity helpers -----------------------------------------
    def _walk_neighbors(self, x: int, y: int):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if self.walkable(nx, ny):
                yield nx, ny

    def _reachable_tiles(self, start: tuple[int, int]) -> set[tuple[int, int]]:
        seen = {start}
        stack = [start]
        while stack:
            x, y = stack.pop()
            for n in self._walk_neighbors(x, y):
                if n not in seen:
                    seen.add(n)
                    stack.append(n)
        return seen

    def _reachable(self, start: tuple[int, int], target: tuple[int, int]) -> bool:
        return target in self._reachable_tiles(start)

    def _carve(self, a: tuple[int, int], b: tuple[int, int]) -> None:
        """Clear a simple L-shaped corridor of GRASS between two tiles."""
        (ax, ay), (bx, by) = a, b
        for x in range(min(ax, bx), max(ax, bx) + 1):
            self.terrain[ay][x] = GRASS
        for y in range(min(ay, by), max(ay, by) + 1):
            self.terrain[y][bx] = GRASS

    # ----- movement ------------------------------------------------------
    def move(self, direction: str) -> MoveResult:
        deltas = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
        if direction not in deltas:
            return MoveResult(BLOCKED, self.player_x, self.player_y)
        dx, dy = deltas[direction]
        nx, ny = self.player_x + dx, self.player_y + dy

        # Bumping a monster attacks it; the player does not move onto its tile.
        mon = self.monster_at(nx, ny)
        if mon is not None:
            return MoveResult(MONSTER, nx, ny, data=mon)

        # Bumping a settlement building uses it; the player stays put.
        bkey = self.buildings.get((nx, ny))
        if bkey is not None:
            return MoveResult(BUILDING, nx, ny, data=bkey)

        if not self.walkable(nx, ny):
            return MoveResult(BLOCKED, self.player_x, self.player_y)

        self.player_x, self.player_y = nx, ny
        if (nx, ny) in self.conn_tiles:
            return MoveResult(CONNECTION, nx, ny, data=self.conn_tiles[(nx, ny)])
        if (nx, ny) in self.resources:
            return MoveResult(RESOURCE, nx, ny, data=self.resources[(nx, ny)])
        if (nx, ny) in self.chests:
            return MoveResult(CHEST, nx, ny)
        return MoveResult(MOVED, nx, ny)

    @classmethod
    def settlement(cls, size: int, buildings, gate_conn_id: str | None = None) -> "BiomeMap":
        """A walkable settlement authored by the player's buildings (not seeded).

        ``buildings`` is an iterable of ``(key, x, y, w, h)``. Every footprint tile
        becomes a **solid** building tile (bumping it returns a ``BUILDING`` result
        carrying the key). A walkable **gate** sits on the bottom edge (the exit) and
        the player **entry** is the free tile just above it. Pure Python — the bridge
        supplies the buildings and the gate connection id.
        """
        terrain = [[GRASS] * size for _ in range(size)]
        bmap: dict[tuple[int, int], str] = {}
        for key, x, y, w, h in buildings:
            for dx in range(w):
                for dy in range(h):
                    if 0 <= x + dx < size and 0 <= y + dy < size:
                        bmap[(x + dx, y + dy)] = key

        # Gate on the bottom edge — prefer centre, else the first free bottom tile.
        cx = size // 2
        gate = next(((gx, size - 1) for gx in [cx, *range(size)]
                     if (gx, size - 1) not in bmap), None)
        # Entry: the tile above the gate, else any free tile.
        entry = (gate[0], size - 2) if gate else (cx, size - 1)
        if entry in bmap or not (0 <= entry[1] < size):
            entry = next(((x, y) for y in range(size - 1, -1, -1) for x in range(size)
                          if (x, y) not in bmap and (x, y) != gate), gate or (cx, cx))

        m = cls(size, terrain, entry, {})
        m.buildings = bmap
        if gate is not None and gate_conn_id is not None:
            m.conn_tiles[gate] = gate_conn_id
        return m

    def aggro_check(self) -> MapMonster | None:
        """Monsters do not move. Return the first monster within ``ENGAGE_RANGE`` of
        the player — it pounces and starts a fight. The player walks freely otherwise
        and chooses what to wake up by stepping next to it."""
        px, py = self.player
        for mon in self.monsters:
            if max(abs(px - mon.x), abs(py - mon.y)) <= ENGAGE_RANGE:
                return mon
        return None
