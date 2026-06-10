# Village & Empire — Design Doc

A second progression loop for **webgame-rpg**: you are a **Viking**. You raid and fight
*in person* (the existing grid game), drag the plunder home, and use it to build a
village. The village makes you stronger so you can raid farther. Do it long enough
and you rise from a lone outcast to a **King**.

This doc is the agreed plan. We build against it slice by slice. Nothing here is
final balance — all numbers live in the DB (admin-tunable), same as the rest of the
game.

---

## 1. The core idea

Clash of Clans and Travian separate *you* from *your base* — there's no character,
just a town. **webgame-rpg already has a hero** who explores, fights, and levels up. That
hero **is** the Viking. So we don't staple a base-builder onto an RPG — the two are
one loop:

> Raid the wilds (the grid game you have) → drag home resources, silver & thralls →
> build and upgrade the village → train an army & build longships → raid bigger NPC
> villages → upgrade the Longhouse → rank up **Outcast → Karl → Hersir → Jarl →
> King** → unlock farther regions and sea raids → eventually raid rival players.

The hero **personally leads raids**: his level and equipped gear scale the army's
power. This is what fuses the two games into one engine.

---

## 2. The progression spine — "become a King"

The **Longhouse** (≈ Clash "Town Hall") has a level. That level **is your rank and
title**, and it gates everything else (you can't build anything higher than your
Longhouse).

| Longhouse Lv | Title          | Feel                                              |
|--------------|----------------|---------------------------------------------------|
| 1–2          | **Outcast**    | Just you and an axe. Survive, scrape first wood.  |
| 3–4          | **Karl**       | First real village, a few warriors, raid camps.   |
| 5–7          | **Hersir**     | Walls, a longship, sea raids, take thralls.       |
| 8–9          | **Jarl**       | A warband, defend retaliation, rich raids.        |
| 10+          | **King**       | Multiple settlements, conquer rival jarls (PvP).  |

Leveling the Longhouse also **expands the buildable grid** (see §5) — more room to
build is the tangible reward for ranking up.

---

## 3. Resources

**v1 starts with three** to keep the first build clean. Silver is folded into the
existing `gold`. Thralls arrive with the raiding slice.

| Resource    | Source                                  | Spent on               |
|-------------|-----------------------------------------|------------------------|
| **Wood**    | Lumber camp + forest tiles / exploration | Buildings, longships   |
| **Stone**   | Quarry/mine + exploration                | Walls, advanced buildings |
| **Meat**    | Farm/pasture + hunting                   | Feeds people & army (upkeep) |
| **Gold** *(existing)* | Plunder, treasure, selling     | Shop (existing town)   |
| **Thralls** *(slice 2)* | Captured in raids             | Boost production buildings |

Resources flow in from **both** the existing combat/exploration **and** the
production buildings.

### Food upkeep (v1: ON, gentle)

People + warriors **consume meat**; farms produce it. If net food goes negative your
village is starving — troops **slowly desert** over time (they do *not* instantly
die). This is Travian's best mechanic: it stops army-spam and forces balancing
economy vs. war. Thematically perfect (Viking winters).

### Storage caps (Clash idea)

Storehouse/Granary cap how much you can hold. A full store wastes production, which
pushes you to **spend or go raid** instead of idling.

### Thralls (slice 2) — the Viking twist

When you win a raid you choose: **slaughter** the enemy (more gold/silver, instant)
or **capture thralls** (less loot now, but they work your production buildings and
permanently boost output). Gives a real strategic choice and a reason not to kill
everyone. Nothing in Clash/Travian does this cleanly.

---

## 4. Buildings & how they interlock

Four clusters that feed each other:

```
   PRODUCTION            STORAGE           MILITARY            PROGRESSION
   Lumber Camp ─wood─┐                    Barracks ─troops─┐
   Quarry ─────stone─┼─► Storehouse ─────► Shipyard ───────┼─► raids ──┐
   Farm/Pasture ─meat┘   (caps! spend     (longships gate  │           │
   (thralls boost all)    or raid)          raid range)    Blacksmith  │
                                                           (crafts hero  │
                                                            gear from    │
                                                            resources)   ▼
   Longhouse ◄────────────── plunder, gold, thralls ◄──── WIN ◄── Wilds / NPC
   (your RANK; gates                                              villages
    everything; level                                            (the grid +
    up = become King)                                            raid targets)
   Walls + Watchtower ◄── defend when retaliation / PvP arrives
   webgame-rpgstone / Skald ─► Renown track + blessings (healing_shrine plugin fits here)
```

- **Longhouse** — rank/title spine; gates all building levels; expands the grid.
- **Lumber Camp / Quarry / Farm** — the three production buildings (wood/stone/meat).
- **Storehouse / Granary** — storage caps.
- **Barracks** — train troops.
- **Shipyard** — build longships; longship level **gates raid range** (farther,
  richer NPC targets). A clean progression gate.
- **Blacksmith** — crafts the weapons/armor the hero already equips, from gathered
  resources. Closes the loop: **resources → gear → stronger hero → bigger raids →
  more resources.**
- **Walls + Watchtower** — defense value (matters once retaliation/PvP exists).
- **webgame-rpgstone / Skald's Hall** — renown/title track + blessings; the existing
  `healing_shrine` plugin theme fits here.

---

## 5. The village grid (free placement)

Clash-style **free placement**, not Travian fixed slots — the village is *yours*.

- Reuses the existing tiled-grid **renderer**, but the **data model flips**: the
  world grid is regenerated from a seed each load; the village layout is **authored
  by the player and persisted**. Each building stores its own `(x, y)` + footprint.
- **Footprints**: buildings occupy different sizes (farm 1×1, Longhouse 2×2…), so
  placement is a small spatial puzzle, not a list. Space pressure = a real decision.
- **The grid grows with Longhouse level** — start cramped (you're an outcast), each
  rank unlocks more buildable tiles.
- **Walls are the exception**: not a building-on-a-tile, but **wall segments** drawn
  along tile edges to enclose the village (a separate "draw the perimeter" mode).
  Watchtowers/gates snap onto walls.

### Layout option chosen: (A) — layout is yours to build

- Raids resolve on **total stats** (army vs. defense numbers); walls add a defense
  value. Placement is about *your* satisfaction + the space puzzle.
- **Not chosen (yet):** (B) layout affects defense *pathing* (attackers path through
  geometry, walls funnel them). That needs pathfinding + an attack simulator — a lot
  more engine work. We upgrade (A) → (B) **only when PvP arrives**, layered on top of
  the same placement data. (A) is not throwaway.

---

## 6. Timers (the one genuinely new mechanic)

The game is event-driven today (you act → something happens). Timers are the first
thing that happens **on its own over time**:

- Buildings take **real time** to build/upgrade; advanced ones take longer. Limited
  concurrent builds (Clash "builders").
- Production buildings generate resources over time.
- On each village load we compute **"what finished and how much was produced while
  you were away"** from stored timestamps (offline catch-up). This is the core new
  calc and lives in `engine/village.py`.

---

## 7. What we borrow, deliberately

- **From Clash:** build timers + limited builders, Longhouse-gates-everything,
  storage caps, raid-for-loot, free grid placement.
- **From Travian:** resource production, **food upkeep on troops** (the best idea in
  either game), a building prerequisite tree, army raid travel time.
- **Uniquely ours:** the hero **personally leads** raids (level & gear scale the
  army), **thralls** as captured labor, and a **renown/title** track that makes
  "become a King" an explicit goal.

---

## 8. PvP — last, and async (the Clash secret)

Clash isn't real-time PvP: you attack a **frozen snapshot** of an offline player's
base; they get a report later. Because webgame-rpg saves everything to Neon, a player's
village is just rows — raiding it is *reading rows*, not a live connection.

Crucially: **a bot village and a real player's village look identical to the raid
engine.** Building NPC villages first is the foundation, not throwaway work.

---

## 9. Build order (slices)

> Architecture rule (unchanged): `engine/` stays pure Python — no Django imports.
> `game/services.py` remains the only bridge between DB rows and engine objects.

1. **Village economy + timers** *(first)*
   - `engine/village.py` — building defs, costs, build-time & production math, the
     offline catch-up calc, food-upkeep balance.
   - Models: `Village` (resource counts + Longhouse level), `Building` (type, level,
     `(x,y)`, footprint, build-finish timestamp).
   - `/village/` section — view buildings, start timed upgrades, watch farms produce,
     spend resources. Free-placement grid (option A).
   - Resources flow from existing combat/exploration **and** production buildings.

2. **Army + NPC raiding**
   - Train troops (Barracks), build longships (Shipyard) to gate raid range.
   - Raid NPC villages — reuse the **combat engine** (bot village = generated stats vs.
     your army; hero level/gear scales it).
   - Win → **loot-or-thralls** choice. Introduce **thralls**.

3. **Defense & retaliation** — walls/towers matter; NPC counter-raids.

4. **Async PvP** *(last)* — matchmaking near your rank; raid snapshots of real
   players' villages; reports. Optionally upgrade layout (A) → (B) pathing here.

---

## 10. Open questions for later

- Exact resource rates, build times, and upkeep numbers (DB-tunable; balance during
  slice 1).
- Whether the village replaces/expands the existing `/town/` or sits beside it.
- Seasons/winter as a time pressure layer (cheap once timers exist; thematic).
- Multiple settlements at King rank (scope of the "multiple villages" endgame).
