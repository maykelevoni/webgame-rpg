# NEXT STEP — open tracks (Vault DONE)

The economy loop and gear systems are in: Castle/Village split, visual pass, stationary
monsters, **iron → Mine → Smithy refine**, **Market sells surplus → gold**, the
**slot-based inventory + paper-doll**, and now the **Vault 💰** (see
`docs/IMPLEMENTATION-STATUS.md` §10). **Every Castle station is now functional.**

## The Vault (💰) — DONE (2026-06-10)
A safe gold stash so death (half-gold penalty) doesn't wipe everything:
- `Character.vault_gold` field (migration 0024) — separate from carried gold, so the
  `combat_action` LOSE branch (`char.gold //= 2`) never touches it.
- Bump 💰 → Deposit/Withdraw panel in `explore.js`. Service `vault_action` (deposit/withdraw,
  int or `"all"`, atomic); JSON endpoints `castle/vault/` + `castle/vault/move/`.
- (Item storage in the Vault was left for later — gold only for now.)

## Parked tracks (pick any)
- **Smithy also sells gear** — buy weapons/armour there (the catalog now has a piece per slot).
- **More biomes** — desert/ice areas wired into the world graph (specs already exist in
  `engine/maps.BIOMES`), dungeon depth scaling.
- **Combat polish** — floating damage numbers, hit flash.
- **More gear per slot** — give the shop variety (better helmets/boots/amulets at higher cost).
- Village slice 2 (army/raiding) is on hold (Harbor was cut).

## Decisions locked
- Materials: wood / stone / meat / iron / gold.
- Equip slots: weapon, shield, helmet, armor, boots, amulet (no gloves/ring).
- Castle stations: Market (buy + sell surplus ✓), Smithy (refine ✓ / buy later), Mead Hall
  (rest ✓), Vault (stash, next). Castle fixed/authored; Village = top-down build screen.
- Refine: hybrid rule (+1..+3 safe, higher can level-down). DONE.

## Conventions & env (must follow)
- `engine/` stays pure Python; `game/services.py` is the only DB↔engine bridge.
- **WSL `/mnt/d`: restart `runserver` after editing `.py`** — **check the port first**
  (`pkill -f "manage.py runserver"`; a stale server may hold `:8000` → you'd test old code).
  Don't chain the server start with `&` in one bash — run it as its own background command.
- Run server: `dangerouslyDisableSandbox: true` + `--noreload`; poll readiness with Python
  `urllib`. A backgrounded server may report a bogus "failed"/exit-1 status — verify via the port.
- **Browser caching:** `browser_navigate` to the same URL may not reload — append `?t=N`.
  Modals can go stale across separate `browser_evaluate` calls — open + act in ONE call.
  For reliable server checks use the Django **test client** (`Client(SERVER_NAME='127.0.0.1')`,
  `force_login`, `HTTP_X_REQUESTED_WITH='fetch'`).
- venv: **`.venv/bin/python`**. Tests: `.venv/bin/python -m pytest -q` (56 green).
- **Don't reset the admin password.** Login `admin` / `admin12345` (char "Ragnar", id 15; has a
  +5 Iron Sword, gear in several slots, and a Mine). Discuss/confirm before large changes.

## Definition of done (Vault) — MET
At the Castle Vault you can deposit/withdraw gold; stashed gold survives death (separate
`vault_gold` field). 56 tests green; verified against the dev DB (deposit/withdraw/overdraw,
gold conserved). In-browser smoke check still recommended after a hard refresh of `explore.js`.
