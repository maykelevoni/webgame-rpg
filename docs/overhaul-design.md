# Overhaul design — World Map hub, modal Castle/Village, real terrain

Locked 2026-06-10 with the user. This replaces several clunky systems with a single
strategic map and modal-driven bases. **Plain names only — no themed naming** (see the
`plain-names-no-theme` rule).

## The problems we're fixing
1. **Biome connections are bad** — walking onto an edge 🚪/🌀 tile to transition is weird.
2. **Raids have no geography** — a hardcoded list with no sense of distance.
3. **The "Castle" never looks like a castle** — it's a grass grid with emoji on it.
4. **The Village placement grid is fiddly** — free-placement puzzle nobody wants.
5. **Water/rock are flat colored blocks** — read as "invisible wall," not terrain.

## The design

### 1. World Map (the new hub) — fixes #1 and #2 together
A strategic, zoomed-out map. **Your Castle sits at the center.** Around it, at varying
distances, are nodes:
- **Your Village** (base management),
- **Biome zones** (Forest, Desert, Snowfield, Cave) — enter to explore,
- **Raid targets** (Bandit Camp, Coastal Village, Enemy Fort, …).

**Tap a node to travel to it. Distance = travel time** (a real timer, reusing the
build-timer / offline-catch-up tech). Close = quick & cheap; far = long march, richer
loot, tougher fights. Travel is **real-time timers** (Last-Day-on-Earth style), not instant.

- Arrive at a **biome** → drop into that biome's walkable grid (the existing tile
  exploration — *kept*, it's the good part). Leaving a biome returns you to the World Map.
- Arrive at a **raid target** → the army resolves the raid there.
- **No more edge-tile transitions.** The World Map is how you move between everything.

### 2. Castle = a drawn castle, services as modals — fixes #3
The Castle stops being a walkable tile grid. It's the **home base at map center, drawn as
an actual castle** (illustration/scene). Its services are **buttons that open modals**:
- 🏪 Market (buy/sell), 🔨 Smithy (refine), 🍺 **Tavern (rest → full HP, clearly labeled)**,
  💰 Vault (stash gold).
No emoji-on-grass. The Tavern heal becomes visible and obviously works.

### 3. Village = tap-a-building modals — fixes #4
The Village shows its buildings on a small **fixed scene** (no free placement). **Tap a
building → a modal** with its options: upgrade, collect, train (Barracks), info. "Build
new" is also a modal (pick from a list). Keeps the base loop, drops the placement puzzle.

### 4. Real water & rock terrain — fixes #5
Inside biomes, impassable tiles get **real terrain visuals** — water tiles (blue with a
wave/edge so you read "walk around water") and rock/cliff tiles with texture and a raised
edge — instead of flat fills. Real sprite tiles where we have them, layered CSS otherwise.

## What we keep
- The **in-biome tile walking** (move, harvest mini-game, monster fights, chests).
- The whole **economy + army** loop already built (production, refine, inventory, vault,
  train/raid). Only the *navigation and presentation* around it changes.

## Build order (each its own shippable slice)
1. **World Map** — ✅ DONE (2026-06-10, slice 1). `engine/travel.py` (pure: distance +
   `travel_seconds`, Castle at centre 50,50). `MapArea.world_x/world_y` + travel fields on
   `Character` (migrations 0029/0030). Services `world_map_payload`/`start_travel`/`arrive`/
   `travel_state`/`enter_castle`; raid targets carry map coords. `/map/` page (positioned
   nodes, distance-based travel timers + JS countdown, Arrive button); nav "Map" + "Explore".
   Biome arrival → enter the grid; raid arrival → resolve the raid.
   **Sync (2026-06-11):** the current node is marked (📍 + ring), its button is "Explore";
   Village is a node; travel time is measured from where you stand (`travel_seconds_from`).
   **Edge-exit (2026-06-11):** LDoE-style — walking off the grid edge returns you to the
   World Map (`maps.EDGE_EXIT` → `do_move` `leave_map` → `/map/`). Biomes now generate with
   **no exit tiles** (the old edge-tile connections are retired). Slice 1 complete.
2. **Castle redraw + service modals** — ✅ DONE (2026-06-11). `/castle/` page: a CSS-drawn
   castle (towers + crenellations + gate + flag), service **buttons** (🏪 Market / 🔨 Smithy /
   🍺 Tavern→rest / 💰 Vault) that open the existing modals — explore.js is now grid-optional
   (reads cfg from `#map-grid` OR `#svc-host`; movement/combat guarded by `if (grid)`); a
   `[data-service]` dispatch + a Tavern rest modal showing HP. Map's Castle node → `/castle/`;
   `/play/` redirects city→`/castle/`; the walkable castle grid is retired (`go_castle` removed).
   Verified in-browser (castle renders; Tavern heals with a clear modal).
3. **Village modals** — fixed building scene, tap → options modal; build-new modal.
4. **Terrain art** — ✅ DONE (2026-06-11). Water = textured, gently-animated ripple pool
   with inset depth; rock = raised beveled cliff; snowfield water is a still frozen variant.
   CSS-only (`base.css`). (Done out of order — it's bounded and low-risk.)

## Open / deferred
- Travel-while-busy rules (can you do other things mid-march?) — decide during slice 1.
- Later army pieces (longships to gate raid range, capture-vs-loot, defense/retaliation,
  async PvP) still queued from `village-design.md` — unchanged by this overhaul.
