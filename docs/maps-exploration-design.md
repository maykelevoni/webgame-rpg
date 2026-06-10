# Maps & Exploration — Design Doc

Turns webgame-rpg's single random field into a **world of connected places**: procedural
biome maps with real terrain you navigate around, visible resources/chests, and
**monsters that hunt you**. This is also how the village finally gets *"resources
from exploration"* (mine → stone, forest → wood).

No map editor — everything is **procedurally generated per biome** from a seed (an
evolution of `engine/world.py`), with the world graph defined in the **DB (admin-
tunable)**.

---

## 1. What changed from the seed-world

Today: one grid, generated from a seed, monsters invisible (random encounters),
only town + treasure placed; the only collision is the outer edge.

Now:
- **Many maps**, each a biome (grass/forest, desert, ice, mine, dungeon, city…).
- **Per-tile collision** — generated **water** and **rocks** are impassable; you
  walk *around* them. The generator guarantees every exit stays reachable.
- **Visible content** — resource nodes, chests, and monsters are entities you can
  see and walk up to (Tibia-style).
- **Monsters aggro** — within a monster's **sight radius** it steps toward you each
  turn and engages on contact (turn-based pursuit; see §4).
- A character's position becomes **`(area, x, y)`**, not `(x, y)` on one world.

---

## 2. World shape — chosen: (A) named overworld + descending dungeons

- A small set of **named surface regions** (e.g. City, Greenwood, Dunes,
  Frostpeak) wired together in a fixed little graph — your persistent world,
  **remembered** (stable seed → same layout when you return; cleared chests/monsters
  tracked per area, like today's `cleared` list).
- **Dungeons/mines descend in fresh procedural levels** — a *hole-with-stairs* or
  *mine entrance* generates a new random level each descent, deeper and deadlier,
  with 1–2 onward exits. Surface = home and familiar; underground = the random run.
- The region graph + connections live in the admin (`MapArea` + `MapConnection`).
  No editor: you add/rename regions and rewire connections as data.

**Connections** are flavored by biome and always include a way **back** plus one or
two **onward**: city → *dungeon entrance*, dungeon → *hole with stairs* (deeper),
grass → *mine entrance*, etc. Walking onto a connection tile transitions you.

---

## 3. Biomes

Each biome is a set of generation rules (admin-tunable where it makes sense):
terrain palette + obstacle density (water/rock/trees), sprite set, monster spawn
table, and which resources its nodes yield.

| Biome    | Terrain & obstacles        | Resources        | Feel              |
|----------|----------------------------|------------------|-------------------|
| Grass/Forest | grass, trees, ponds    | wood, meat       | gentle, open      |
| Desert/Sand  | sand, rocks, dunes     | stone            | sparse, hot       |
| Ice      | snow, ice, frozen water    | stone, meat      | slippery, harsh   |
| Mine     | rock walls, ore veins      | stone (ore)      | tight, maze-like  |
| Dungeon  | stone floor, walls, pits   | (loot/chests)    | dangerous, deep   |
| City     | paths, buildings           | (shop/village)   | safe hub          |

**Resources feed the village** — harvesting a node adds wood/stone/meat to your
`Village` stockpile (the loop we deferred from the village design). Nodes are
visible; walk up and harvest; the tile is then spent (tracked in `cleared`).

---

## 4. Monsters: visible + turn-based pursuit

- Monsters are **entities with positions** on the map (not random rolls), drawn from
  the biome's spawn table, placed by seed.
- Each monster has an admin-tunable **sight radius**. When the player steps within
  it, the monster **moves one tile toward the player** (greedy step, **respecting
  collision** — it can't cross water/rock either). On contact (adjacent/same tile)
  **combat starts**, reusing the existing `Combat` flow.
- **Turn-based pursuit:** monsters move when *you* move. Stand still and they freeze
  (the server only runs on your action). This still feels alive — you can't stroll
  past a wolf; it intercepts you, and you use terrain to break the chase or get
  cornered. Real-time idle-chase is a **later, optional** layer (needs a client-side
  tick); not in scope now.

---

## 5. Architecture (unchanged rules apply)

`engine/` stays pure Python; `game/services.py` is the only DB↔engine bridge.

- **`engine/maps.py`** (new) — biome generation from `(seed, biome, size)`:
  terrain + collision, connectivity guarantee, placement of resource nodes / chests
  / monster entities; collision-aware player movement; `step_monsters(player)` for
  turn-based pursuit; connection tiles. All deterministic from the seed + a
  per-area `cleared` set.
- **Models** — `MapArea` (key, name, biome, seed, size, is_start), `MapConnection`
  (from_area, to_area, kind: door/mine/hole/stairs/portal). `Character` gains
  `current_area` (FK) and per-area cleared state (JSON keyed by area). `Monster`
  gains `sight_radius` (+ optional biome tag for spawn tables).
- **Bridge/`do_move`** — collision check, harvest node → village, open chest →
  gold/loot, run monster pursuit, contact → start combat, connection → switch area.
- **View/template** — render terrain + entities (resources/chests/monsters/exits)
  on the existing grid renderer; movement via the existing d-pad (no JS).

---

## 6. Build order (slices)

1. **Biome maps + collision + aggro** *(first)* — `engine/maps.py` with one surface
   biome (grass + water/rock you walk around, connectivity-guaranteed), **visible
   monsters with turn-based pursuit**, **visible resource nodes** feeding the
   village, chests, and **working connections** (one surface region + one dungeon
   descent). Replaces the seed-world view; town/shop/village stay reachable.
2. **More biomes & the region graph** — desert/ice/forest/mine generation, the
   named overworld wired in the admin, dungeon depth scaling.
3. **Polish** — pathfinding niceties (lose aggro via line-of-sight), richer chest
   loot, biome-specific resources, minimap.
4. **(Optional, later)** real-time idle-chase tick.

---

## 7. Open questions for later

- How the existing **town/shop** and the **village** attach to the City region
  (a tile you enter, or a connection).
- Whether surface regions ever regenerate (events/seasons) or stay fixed forever.
- Dungeon depth rewards & difficulty curve (DB-tunable).
