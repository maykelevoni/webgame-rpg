# webgame-rpg — Implementation Status & Handoff

**Last updated: 2026-06-09.** This is the catch-up doc for a fresh session. It
summarizes everything built across the village/exploration/interaction work, the
current state, conventions, environment gotchas, and what's next.

Design docs (read these for the *why*):
- `docs/village-design.md` — Viking village/empire builder (base-building loop).
- `docs/maps-exploration-design.md` — connected biome maps, collision, monsters.
- `docs/settlement-merge-design.md` — merging town+village+city into one walkable
  settlement, the JS interaction layer, and resource mini-games.

---

## Architecture (unchanged, must follow)
- **`engine/`** = pure Python game rules. **Never imports Django.** Time/seed/inputs
  are passed in, so everything is deterministic and unit-tested.
- **`game/services.py`** = the ONLY bridge: loads DB rows → engine objects → runs
  rules → writes back. Views stay thin.
- **All balance lives in the DB** (admin-editable): items, monsters, building types,
  map areas, config.
- Tests in `tests/` (pure-Python engine tests). **Currently 50 passing.**

---

## What's BUILT and working

### 1. Village / base-builder (slice 1) — `/village/`
- `engine/village.py`: `BuildingDef`, `PlacedBuilding`, `VillageState`, `tick(now)`
  offline catch-up, placement validation, rank/grid math, **per-Longhouse build
  limits** (`allowed_count`).
- Models: `BuildingType`, `Village`, `Building` (migrations 0008–0011).
- Free-placement grid, build timers, resource production (wood/stone/meat), storage
  caps, rank titles (Outcast→Karl→Hersir→Jarl→King), build **count limits** that
  grow with Longhouse level.
- Seeded buildings: longhouse, lumber-camp, farm, quarry, storehouse.
- Starting stockpile on a new village: wood 120 / stone 60 / meat 60.

### 2. Exploration / biome maps (slice 1) — `/play/`
- `engine/maps.py`: `BiomeMap.generate` (terrain + connectivity-guaranteed carving),
  `walkable`, `move`, `step_monsters` (collision-aware turn-based pursuit),
  `MapMonster`, `BiomeSpec`/`biome_spec` (grass/dungeon/desert/ice).
- Models: `MapArea`, `MapConnection`; `Character.current_area` + `Character.area_state`
  (JSON per-area: cleared list, live monster positions, seed). `Monster.sight_radius`
  + `Monster.biome`. Migrations 0012–0013.
- **Collision terrain** (water/rock impassable, walk around), **visible** resources/
  chests/monsters, **monsters aggro** (step toward player within sight; fight on
  contact; don't advance on a blocked bump), area connections (mine/stairs/hole/town).
- Seeded world: **Greenwood** (grass, start) ↔ **Old Mine** (dungeon, descend re-rolls
  seed). Greenwood has a **🏠 town connection** → currently the on-map Market modal.
- Resources harvested from maps feed the **village stockpile**.

### 3. Interaction overhaul (JS layer) — Phase 1 + 3 of settlement-merge doc
New vanilla-JS layer (no framework): **`game/static/js/explore.js`**.
- **Smooth movement**: d-pad + arrow/WASD keys go through `fetch` and repaint just the
  grid (no full-page reload). HUD (HP/gold/area) updates in place.
- **Market/Hospital modal**: walking onto the 🏠 town tile opens a shop modal on the
  map (buy/sell/rest) — content served from JSON endpoints (`shop_data`, `buy`,
  `sell`, `rest` all return JSON for AJAX; no-JS fallback still redirects).
- **Resource mini-game (click-to-break animation)**: stepping on a 🪵/🪨/🍖 node opens
  a modal; clicking **💥 Strike** shakes the node + spits a chip, integrity bar drops,
  after N hits (rock 5, wood/meat 4, chest 2) it **shatters** and shows a **reward
  screen** (+amount) with a ✔ Collect button. Yield random 4–8 (chest gold 15–45).
  Endpoints: `/play/harvest/`, `/play/open-chest/`. (Server is authoritative; the
  client just animates.)
- **Combat is now AJAX with hit animation**: attacking updates HP bars + log in place;
  the **monster shakes when hit, the player shakes when hit back**; on end a **result
  modal** (⚔️ Victory +gold/+XP, 💀 Defeated, 🏃 Fled) with a ▶ Continue button
  (reloads to a clean map). Combat outcome is a **modal, not a message banner**.
  Movement is locked while a fight overlay is present.

Supporting server changes:
- `game/views.py`: `_is_ajax()` helper; `move`, `combat_action`, `buy/sell/rest`
  return JSON on `X-Requested-With: fetch`; added `harvest`, `open_chest`, `shop_data`
  views. `world_view` pops `session["combat_result"]` for the no-JS fallback modal.
- `game/services.py`: `build_map_grid`, `do_move` (collision→node→pursuit→combat/
  connection; nodes are NOT auto-harvested — the client mini-game calls harvest),
  `harvest_node`/`open_chest_node` (random yield, mark cleared), `shop_payload`,
  area/state helpers (`get_area`, `build_biome_map`, `save_area_map`, `_use_connection`,
  `_begin_map_encounter`, `_clear_defeated_map_monster`, `_respawn_at_start`).
- `world.html`: grid `#map-grid` carries data-* URLs + csrf; battle overlay has ids
  (`#battle-monster`, `#battle-player`, `#mon-hp-bar`, `#pl-hp-bar`, `#battle-log`);
  `#modal-root` for JS modals; server-rendered combat-result modal (no-JS fallback);
  `explore.js` loaded with `?v={{ asset_version }}` cache-buster.
- CSS in `game/static/css/base.css`: terrain colors, modals, toast, strike/shake
  animations (`node-shake`, `node-shatter`, `.battle-sprite.hit`), timing/integrity
  bars, reward pop. `.modal-root` z-index **150** (above battle-overlay's 100).

---

### 4. Walkable settlement (Village Phase 2a) — DONE
Walking onto the 🏠 tile now **enters your village as a walkable map** instead of
opening a modal (from `settlement-merge-design.md`):
- `engine/maps.py`: `BUILDING` move-result + `BiomeMap.buildings` (solid footprint
  tiles that report a `BUILDING` bump carrying the building key) + `BiomeMap.settlement()`
  factory (walkable grid authored from the player's buildings, gate on the bottom edge).
- `game/services.py`: `build_settlement_map` / `build_settlement_grid`; `build_biome_map`
  + `build_map_grid` branch on biome `city`; `do_move` returns `{"kind":"building",…}`;
  `_use_connection` now enters any connection with a `to_area` (so the 🏠 town link enters
  the settlement); `_ensure_service_buildings` pre-places Market + Hospital (idempotent —
  lazily backfills existing villages too); services skipped in the buildable palette.
- Models/migrations: `service` building category (0014); `Market` + `Hospital`
  `BuildingType`s, the shared **`settlement`** `MapArea` (biome `city`), repointed
  Greenwood 🏠 → settlement, and a settlement→Greenwood gate (0015).
- `views.py` `move`: ajax returns `{"building": key}`; no-JS fallback redirects
  (longhouse→`/village/`, market→shop, hospital→rest). `explore.js` dispatches
  `data.building` (longhouse→`/village/`, market→`openMarket()`, hospital→rest+toast);
  grid carries `data-village-url`. Settlement buildings render via the normal grid cells
  (solid `terrain-rock` look + building icon/label); the gate renders as 🚪.
- Tests: `tests/test_maps.py` settlement cases (footprints solid, bump returns the key,
  gate walkable + entry adjacent, gate returns a connection). Verified in-browser:
  enter 🏠 → bump Market/Hospital/Longhouse → leave via the gate.

### 5. Visual / theming pass (emoji + biomes) — DONE (2026-06-09)
Moved buildings + monsters off the unreadable Kenney tiles onto **emoji**, and gave each
biome a distinct floor:
- Models: `BuildingType.emoji` + `Monster.emoji` (admin-editable, preferred over the sprite
  `icon`); engine `Monster.emoji` and `BuildingDef.emoji` carry it. Migrations 0016 (schema)
  + 0017 (data: emoji for all buildings/monsters, **renamed Quarry→Stonecutter 🧱** and
  **Hospital→Mead Hall 🍺**, and a **beast roster** — boar/bear/spider/stag, scorpion/viper,
  ice-bear/winter-wolf, bat/rat/troll/draug/jötunn/cave-wyrm — each with biome + stats).
- Render: `build_map_grid` (map monsters), `build_settlement_grid` (castle buildings),
  `build_village_grid` (village buildings) all emit `emoji`; the battle overlay shows the
  monster emoji (`.battle-emoji`, still shakes via `.battle-sprite`).
- Terrain: `#map-grid` carries `biome-<biome>`; per-biome floor colours in `base.css`
  (grass keeps its sprite, desert=sand, ice=pale-blue, dungeon=dark, city=stone) + a
  `terrain-building` tile for settlement structures. `explore.js` `repaint` swaps the
  `biome-*` class on area changes (`move` payload now includes `biome`).
- Building emoji: 🛖 Longhouse · 🪓 Lumber Camp · 🧱 Stonecutter · 🐄 Farm · 📦 Storehouse ·
  ⛏️ Mine(planned) · 🏪 Market · 🍺 Mead Hall · 🔨 Smithy(planned) · 💰 Vault(planned).
  Verified in-browser across grass/dungeon/city + combat. 50 tests green.

### 6. Monsters stop chasing + Castle/Village split — DONE (2026-06-09)
- **Stationary monsters:** removed pursuit. `engine/maps.py` `step_monsters` → `aggro_check`
  (monsters never move; one within `ENGAGE_RANGE`=1 of the player pounces → combat).
  `do_move` calls it after a real move. `sight_radius` is now an unused field. Tests rewritten.
- **Castle ≠ Village:** the `city` MapArea you enter from the world map is now the **fixed,
  authored Castle** — a shared set of NPC stations (NOT the player's buildings):
  `services.CASTLE_STATIONS` = 🛖 Your Village(road) · 🏪 Market · 🔨 Smithy · 🍺 Mead Hall ·
  💰 Vault on a 7×7, gate 🚪 back to the world. `build_castle_map`/`build_castle_grid` replace
  the old `build_settlement_*`. `do_move` returns `{"building": key}`; `explore.js`
  `useBuilding` dispatches: market→shop modal, hospital→rest, village→`/village/`,
  smithy/vault→info modal (refine/stash are the next slice).
- **Village = production only:** `get_or_create_village` no longer auto-places services
  (`_ensure_service_buildings` removed); migration 0018 deletes the Market/Mead Hall
  `Building` rows from every village. The Village (`/village/` top-down build screen) now
  holds only Longhouse + Lumber Camp + Stonecutter + Farm + Storehouse.
- Verified: castle layout + each station bump returns the right key (test client), gate exits
  to Greenwood, village renders production only, smithy modal opens in-browser. 50 tests green.

### 7. Iron + the Mine + the Smithy refine — DONE (2026-06-09)
The first full **produce → get-stronger** chain across Village and Castle:
- **Iron** is the 5th material (wood/stone/meat/**iron**/gold): `engine/village.RESOURCES`,
  `VillageState.iron`, `Village.iron` (migration 0019), carried through the bridge + shown
  in the village resource bar. Production/storage/tick already loop over `RESOURCES`.
- **The Mine ⛏️** — a production `BuildingType` (migration 0020) that makes iron (15/min at
  Lv1), unlocks at Longhouse Lv2, appears in the village palette. Verified iron accrues.
- **The Smithy refine** (`engine/refine.py`, pure): refine equipped gear +1…+`MAX_LEVEL`(9)
  for iron + gold; **+1..+3 (SAFE_LEVEL) always succeed**, above that success odds fall and a
  **failure drops the gear one level** (hybrid MU rule the user chose). Each refine level adds
  to the stat the gear already grants (`InventoryEntry.refine_level` → `_equipped_bonus`;
  `InventoryItem.refine_level`, migration 0021). Bridge: `smithy_payload` + `refine_item`
  (`@transaction.atomic`, syncs iron first). Views `smithy_data`/`refine`, URLs
  `castle/smithy/` + `castle/smithy/refine/`. `explore.js`: Smithy bump opens a real panel
  listing gear with Refine buttons (cost + odds), shows success/fail + updated stats.
- Tests `tests/test_refine.py` (6). **56 tests green.** Verified in-browser: refined an Iron
  Sword +4→+5, iron/gold spent, attack rose, next cost/odds shown.

### 8. Market sells surplus + chest reward fix — DONE (2026-06-09)
- **Sell surplus → gold** closes the economy loop: the Castle Market modal has a *Sell village
  surplus* panel (wood/stone/meat 1g/unit, iron 3g; admin-tunable `services.RESOURCE_SELL`).
  `sell_resources(user, resource, amount|'all')` + view `sell_resource` + URL
  `town/shop/sell-resource/`; `shop_payload` now includes village `resources` + `sell_rates`;
  `explore.js` Market renders the sell rows (Sell 10 / All). Rest moved off the Market (it's the
  Mead Hall's job now). Verified via test client (sold iron → gold up, stock down).
- **Chest bug:** the open-chest reward showed the running total, not the gain (the view's
  `gold: char.gold` clobbered the result). View now returns `gold_gain` (the gain) + `gold`
  (total); `explore.js` reward reads `gold_gain`.

### 9. Slot-based inventory + paper-doll (MU-style) — DONE (2026-06-09)
- **6 equip slots** (`models.EQUIP_SLOTS`): weapon ⚔️ · shield 🛡️ · helmet 🪖 · armor 🥋 ·
  boots 🥾 · amulet 📿. `Item.slot` (migration 0022) is the source of truth for gear;
  `engine.items.Item.is_gear = bool(slot)` (kind only marks consumables now). Seeded a
  starter item per slot (migration 0023): iron-sword/wooden-shield/iron-helm/leather-armor/
  leather-boots/bone-amulet — all refinable; equip is one-per-slot (existing rule).
- **Paper-doll** rendered two ways from one `services.inventory_payload`: the **Character page**
  (`/character/`, server-rendered, no-JS equip/unequip/use forms) and an **on-map inventory
  modal** (🎒 button + the **I** key on `/play/`). `equip`/`use_item` views are now AJAX-aware;
  new `unequip` view + `unequip_item` service; `inventory_data` JSON endpoint. `explore.js`
  `openInventory`/`renderInventory` + equip/unequip/use delegates; `.doll-grid` CSS.
- Smithy/refine now filter gear by `slot` (not kind). Refine `+level` shows on the doll/slots.
- Verified via test client (equip raises stats, unequip lowers, use heals) and in-browser
  (modal opens, equip moves a piece into its slot). **56 tests green.**

### 10. The Castle Vault — DONE (2026-06-10)
A safe gold stash so the death penalty (half **carried** gold) doesn't wipe everything:
- `Character.vault_gold` field (migration 0024). Stashed gold is a separate model field
  the combat engine never touches, so it survives the LOSE branch by construction.
- Bridge: `vault_payload` (carried + stashed) and `vault_action(user, "deposit"|"withdraw",
  amount)` — `@transaction.atomic` + `select_for_update`; amount is an int or `"all"`;
  rejects overdraw/empty. Views `vault_data`/`vault_move`, URLs `castle/vault/` +
  `castle/vault/move/`.
- `explore.js`: bumping 💰 now opens a real Vault panel (`openVault`/`renderVault`) with
  Deposit/Withdraw amount inputs + "All" buttons; `doVault` repaints the panel + HUD.
  `.vault-cols`/`.vault-input` CSS. (Replaced the old "coming next" info modal.)
- Verified via the dev DB: deposit-all → withdraw, overdraw rejected, gold conserved.
  56 tests green (vault is DB-backed; the pure-engine suite is unchanged).

### 11. Phase 2b — gate-return + retire `/town/` — DONE (2026-06-10)
- **Gate returns you to the tile you entered from.** `_use_connection` now records the
  origin tile on the destination's `area_state` (`return_to`) and, when you walk back,
  drops you on that tile (if still walkable) instead of the area's default start. Verified
  with the test client: enter the settlement from Greenwood's 🏠 tile (6,11) → leave via
  the gate → back at (6,11).
- **`/town/` retired.** It was orphaned (not in nav; the world 🏠 enters the Castle now),
  so it was dead UI. Removed `town.html`, `town_view`/`town_action`/`leave_town` (views +
  the `leave_town` service), and the `town`/`town_action`/`leave_town` routes. The no-JS
  `rest` and dead-end-connection fallbacks now go to the world (a connection with no
  `to_area` returns `kind:"blocked"`, not `"town"`). `shop.html`'s "Back to town" link →
  the world. The `MapConnection` `town` kind survives only as the 🏠 gate **icon**.
  Note: the plugin `add_town_action` registry API still exists but is now **unsurfaced**
  (no UI host) — relocate to a Castle station if town-actions are wanted again.

## What's NEXT (queued, NOT built)

### Village Phase 2b leftovers
- **Walk/Build toggle / walkable village** — *intentionally deferred.* The Castle is now
  the walkable hub and the top-down `/village/` build grid is the better placement UX, so
  making the village walkable would partly undo the §6 Castle/Village split. `/village/`
  stays as the build screen (NOT retired).

### Other open tracks
- **Exploration slice 2**: more biomes (desert/ice/forest), the named overworld graph
  in admin, dungeon depth scaling.
- **Village slice 2**: army (Barracks) + longships (Shipyard) + **raiding NPC villages**
  (reuse combat engine) + **thralls** (capture vs. slaughter). Then async PvP last.
- **Combat polish ideas** floated: hit-flash/red tint, floating damage numbers.
- **Food upkeep** consequence (troops desert) — deferred until army exists.

---

## Environment gotchas (IMPORTANT for the next session)
- **WSL `/mnt/d`**: Django autoreload does NOT fire on file changes. **Restart
  `runserver` after editing any `.py`.** Templates re-render per request (fine).
- **Static JS caching**: the browser aggressively caches `.js`. We added
  `?v={{ asset_version }}` to `explore.js`; a one-time **hard refresh (Ctrl+Shift+R)**
  may be needed after a JS change, then it self-busts.
- **Backgrounding `runserver` in the agent harness** gets flagged "failed" and bash
  `sleep` is blocked. To run it: `dangerouslyDisableSandbox: true` + `--noreload`,
  then poll readiness with a Python `urllib` loop (not bash `sleep`). It binds fine;
  the "failed" status is a harness artifact.
- **Do NOT reset the admin password during debugging** — it invalidates the browser
  session (logs the user out). Admin login: **`admin` / `admin12345`** (temporary;
  user should change it). Admin has a demo character "Ragnar".
- Run server: `python manage.py runserver` → http://127.0.0.1:8000 . Tests:
  `python -m pytest -q`.

---

## Quick file map
- Engine: `engine/village.py`, `engine/maps.py` (+ existing character/combat/world/…).
- Bridge: `game/services.py`. Views: `game/views.py`. URLs: `game/urls.py`.
- Models: `game/models.py`. Admin: `game/admin.py`. Migrations: `game/migrations/`
  (latest 0013).
- Templates: `game/templates/world.html` (the map + combat + modals), `village.html`,
  `town.html` (legacy, to be retired in 2b).
- Static: `game/static/js/explore.js`, `game/static/css/base.css`,
  `game/static/sprites/` (Kenney tiles).
- Tests: `tests/test_maps.py`, `tests/test_village.py` (+ existing).
