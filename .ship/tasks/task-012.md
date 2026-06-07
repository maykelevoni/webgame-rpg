# Task 012: Combat, town, shop, rest, equip, use-item

## Type
ui

## Description
The interaction screens: turn-based combat, the town menu, the shop (buy/sell),
resting, and equipping/using items. Completes the core gameplay loop.

## Files
- `game/templates/combat.html` (create)
- `game/templates/town.html` (create)
- `game/templates/shop.html` (create)
- `game/views.py` (modify — combat/town/shop/rest/equip/use_item views)
- `game/urls.py` (modify — add routes)

## Requirements
1. Combat (`/combat/`, `/combat/action/`): show player vs monster HP + turn log.
   Actions: Attack, Use item (potion), Flee → call `services.combat_action`. On win:
   apply gold+xp (+ plugin `on_victory`), mark the monster tile cleared, return to world.
   On lose: send to a defeat state (e.g. revive at town with penalty or restart) — keep simple.
2. Town (`/town/`): menu with Shop, Rest (POST `/town/rest/`), Leave (back to world),
   plus any plugin-registered town actions (rendered from the active registry).
3. Shop (`/town/shop/`): list catalog items with buy buttons (deduct gold) and the
   character's sellable items with sell buttons (add gold). Validate affordability.
4. Rest: spend `rest_cost` gold to restore HP to max.
5. Equip (`/character/equip/`) and Use-item (`/character/use-item/`) endpoints used by
   the character sheet and combat.
6. All POSTs CSRF-protected; flash messages for results. Responsive + themed.

## Acceptance Criteria
- [ ] Full loop works: fight → win → gold/xp → level up → town → buy → equip → stronger.
- [ ] Potion usable both in combat and from the sheet; equipping changes stats.
- [ ] Shop buy/sell adjusts gold and inventory correctly; rest heals for gold.
- [ ] Plugin-registered town actions appear when the plugin is enabled.

## Dependencies
- Task 011

## Commit Message
feat(web): combat, town, shop, rest, and equipment flows
