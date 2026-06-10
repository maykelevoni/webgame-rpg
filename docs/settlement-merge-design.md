# Merged Settlement + Interaction Overhaul — Design Doc

Three things that all mean "home" collapse into one: the **town** page, the
**village** build-grid, and the wished-for **castle/city**. They become a single
**walkable settlement** you build *and* live in. Plus a real **client-side JS layer**
for smooth movement, walk-up **modals**, and **resource mini-games** — the game gets
physical instead of "walk onto thing, number goes up."

This supersedes the "town stays a menu" notes in
[village-design] and [maps-exploration-design].

---

## 1. The merged settlement

**The village build-grid *is* the castle map.** One tile grid, two modes:

- **Walk mode** (default): move your character around the settlement — paths between
  buildings, walls at the edges. Buildings are solid; you walk up to them.
- **Build mode** (toggle): the existing village placement (pick building → drop on
  tile, footprints, timers, build limits). You're designing the castle's layout.

**Buildings are entered by bumping them** (reusing the bump that triggers monster
combat — here it opens a **modal**):

| Building            | Bump opens…                          |
|---------------------|--------------------------------------|
| **Market**          | buy/sell shop (replaces the town shop) |
| **Hospital**        | heal / rest                          |
| **Longhouse**       | manage settlement: rank, upgrades, build mode |
| **Lumber/Quarry/Farm** | collect produced resources (still tick over time) |
| **Blacksmith**      | craft/upgrade gear *(later)*         |
| **Barracks**        | train/manage army *(village slice 2)* |

**Entry from the world:** the world-map **gate/town tile** drops you at the
settlement entrance; you walk in. No separate page — it's the safe hub area, a real
place in the world.

**What this retires/repurposes:**
- The **town page** (`/town/`, `town.html`) → becomes the Market modal + the
  settlement map. `rest` → Hospital modal. Shop → Market modal.
- The **village page** (`/village/`) → becomes Build mode on the settlement map; the
  placement/upgrade logic (`engine/village.py`, `Building`/`BuildingType`) is reused
  as-is — buildings just also render as walkable structures.
- Market & Hospital become **building types** (placed or pre-built in a new village).

**Why it's the right version:** one coherent "seat of power" you build, walk, and
defend; the build-grid gains a visible payoff; the castle-with-services wish is met
*using the building system we already have*; and walls/tower placement will matter
once raiders attack this real map.

---

## 2. Resource mini-games

Bumping a rock / tree / chest opens a quick **skill mini-game modal**; yield scales
with how well you do (instead of instant, boring pickup):

- **Timing bar (default for nodes):** a marker sweeps a bar; click in the green
  sweet-spot for a good hit; a few good hits break the node, perfect hits give bonus.
- **Click-to-chip (alt):** click to deplete the node's "HP"; it visibly cracks.
- **Chest = lockpick:** a small stop-the-marker game to crack it open.

Start with the **timing bar** for rock/tree and a simple click-open for chests.

---

## 3. The JS layer (new — vanilla, no framework)

The game has been almost no-JS. To make movement and interaction feel good we add a
small, clean vanilla-JS layer:

- **Smooth movement:** moves go through `fetch` and re-render just the grid in place
  (no full-page reload / flash), with a short CSS slide so a step *animates* one tile.
  This is the main fix for "monster following looks weird" — they'll glide a tile
  instead of teleporting on a reload.
- **Modals:** Market/Hospital/Longhouse and the mini-games are overlays on the map
  (like the existing combat overlay), opened by bumping a building/node.
- **Graceful fallback:** the existing POST d-pad keeps working if JS is off (the
  server endpoints stay authoritative; JS just calls them and paints the result).

Also smooth the **monster pursuit logic**: don't step monsters on a blocked bump, and
soften the L-shaped path so it reads as stalking, not a robot.

---

## 4. Phased plan

> Architecture rule holds: `engine/` stays pure Python; `game/services.py` is the
> only DB↔engine bridge. New JS lives in `game/static/js/`.

1. **JS movement + service modals.** A movement/render JS module: `fetch` the move,
   repaint the grid, animate the step; fix monster pursuit feel. Convert the Market
   (shop) and Hospital (rest) into **modals** opened on the map. (Town page still
   reachable as a fallback during this phase.)
2. **Merge village onto the walkable settlement.** A `city` biome that renders the
   player's placed `Building`s as walkable structures; **Walk/Build mode toggle**;
   bump-to-enter opens the right modal; Market & Hospital become building types
   (pre-built in new villages). Retire `/town/` and the standalone `/village/` page.
3. **Resource mini-games.** Timing-bar modal for rock/tree (yield scales with skill),
   click-open for chests; wire results back to the village stockpile.

---

## 5. Open questions for later

- Exact Walk/Build toggle UX (button vs. entering the Longhouse to build).
- Whether the settlement is one of several (multiple villages at King rank).
- Mini-game difficulty scaling (better tools = easier sweet-spot).
- Defense layout mattering once async raids arrive (ties to [village-design] §5).
