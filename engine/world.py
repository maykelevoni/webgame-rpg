"""The overworld: a square grid the player walks across.

The map is generated *deterministically* from a seed, so the same character always
sees the same world (the seed is saved on the character). Monsters and treasure are
placed on random tiles; once you defeat a monster or open a chest, that tile's
coordinate is added to the character's ``cleared`` list and is left empty from then on.

Like the rest of the engine, this file is pure Python — no Django, no database.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

# Tile types
EMPTY = "empty"
TOWN = "town"
MONSTER = "monster"
TREASURE = "treasure"

# Movement directions -> (dx, dy). y grows downward (row 0 at the top).
DIRECTIONS = {
    "north": (0, -1),
    "south": (0, 1),
    "west": (-1, 0),
    "east": (1, 0),
}

# Move outcomes
MOVED = "moved"
BLOCKED = "blocked"


@dataclass
class MoveResult:
    kind: str            # MOVED / BLOCKED / TOWN / MONSTER / TREASURE
    x: int
    y: int


class World:
    def __init__(self, size: int, town: tuple[int, int],
                 monsters: set[tuple[int, int]], treasures: set[tuple[int, int]],
                 player: tuple[int, int]):
        self.size = size
        self.town = town
        self.monsters = monsters
        self.treasures = treasures
        self.player_x, self.player_y = player

    # ----- construction --------------------------------------------------
    @classmethod
    def generate(cls, seed: int, cfg, cleared: list | None = None,
                 player: tuple[int, int] | None = None) -> "World":
        """Build a world from a seed + config, skipping already-cleared tiles."""
        size = cfg.grid_size
        rng = random.Random(seed)
        cleared_set = {tuple(c) for c in (cleared or [])}

        # The map layout depends ONLY on the seed/size — never on where the player
        # currently stands — so the world stays stable as the player walks around.
        # We anchor placement on the centre tile (kept empty) and put the player
        # there by default; their live position is passed in separately.
        anchor = (size // 2, size // 2)

        taken = {anchor}
        town = cls._pick_tile(rng, size, taken)

        monsters: set[tuple[int, int]] = set()
        for _ in range(cfg.monster_count):
            monsters.add(cls._pick_tile(rng, size, taken))

        treasures: set[tuple[int, int]] = set()
        for _ in range(cfg.treasure_count):
            treasures.add(cls._pick_tile(rng, size, taken))

        # Remove anything the player has already dealt with (town is permanent).
        monsters -= cleared_set
        treasures -= cleared_set

        player_pos = player or anchor
        return cls(size, town, monsters, treasures, player_pos)

    @staticmethod
    def _pick_tile(rng: random.Random, size: int, taken: set) -> tuple[int, int]:
        """Pick a random free tile, recording it so it isn't reused."""
        while True:
            pos = (rng.randrange(size), rng.randrange(size))
            if pos not in taken:
                taken.add(pos)
                return pos

    # ----- queries -------------------------------------------------------
    @property
    def player(self) -> tuple[int, int]:
        return (self.player_x, self.player_y)

    def tile_type(self, x: int, y: int) -> str:
        if (x, y) == self.town:
            return TOWN
        if (x, y) in self.monsters:
            return MONSTER
        if (x, y) in self.treasures:
            return TREASURE
        return EMPTY

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.size and 0 <= y < self.size

    # ----- movement ------------------------------------------------------
    def move(self, direction: str) -> MoveResult:
        """Try to move one tile. Returns what happened (and updates position)."""
        if direction not in DIRECTIONS:
            return MoveResult(BLOCKED, self.player_x, self.player_y)
        dx, dy = DIRECTIONS[direction]
        nx, ny = self.player_x + dx, self.player_y + dy
        if not self.in_bounds(nx, ny):
            return MoveResult(BLOCKED, self.player_x, self.player_y)

        self.player_x, self.player_y = nx, ny
        kind = self.tile_type(nx, ny)
        if kind == EMPTY:
            kind = MOVED
        return MoveResult(kind, nx, ny)

    # ----- rendering helper ----------------------------------------------
    def render_grid(self) -> list[list[dict]]:
        """A 2D list of cell descriptors for templates: rows of {type, is_player}."""
        rows = []
        for y in range(self.size):
            row = []
            for x in range(self.size):
                row.append({
                    "type": self.tile_type(x, y),
                    "is_player": (x, y) == self.player,
                    "x": x,
                    "y": y,
                })
            rows.append(row)
        return rows
