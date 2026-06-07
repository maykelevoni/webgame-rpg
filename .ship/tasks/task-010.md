# Task 010: Home, character creation, character sheet

## Type
ui

## Description
The entry flow: a landing page, creating/naming a character, and viewing the
character sheet (stats, gold, equipped gear, inventory).

## Files
- `game/templates/home.html` (create)
- `game/templates/character_create.html` (create)
- `game/templates/character_sheet.html` (create)
- `game/views.py` (modify — `home`, `character_create`, `character_sheet`)
- `game/urls.py` (modify — add routes)

## Requirements
1. `home`: if not logged in → links to login/signup; if logged in with a character →
   "Continue" to `/play/`; if logged in without one → link to create.
2. `character_create` (`@login_required`): form for a name; creates a `Character` via
   `services.get_or_create_character`, assigns a random `map_seed`, applies starting
   stats from `GameConfig`, then redirects to `/play/`.
3. `character_sheet` (`@login_required`): show level, xp (+ to next), hp/max_hp, gold,
   effective attack/defense, equipped weapon/armor, and inventory list with
   equip/use buttons (POST to existing endpoints — wired in Task 012).
4. Responsive panels; uses theme CSS variables.

## Acceptance Criteria
- [ ] New user → create character → lands in `/play/`.
- [ ] Character sheet shows correct derived stats (including gear bonuses).
- [ ] Home routes correctly for the 3 states (anon / no char / has char).

## Dependencies
- Task 009

## Commit Message
feat(web): home, character creation, and character sheet
