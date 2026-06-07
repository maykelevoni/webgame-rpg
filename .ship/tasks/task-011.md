# Task 011: World view + movement UI (grid, D-pad, arrow keys)

## Type
ui

## Description
Render the 10×10 grid and let the player move. Movement works with zero JS
(D-pad buttons) and is enhanced with arrow keys on desktop. Mobile-first.

## Files
- `game/templates/world.html` (create)
- `game/static/js/keys.js` (create)
- `game/views.py` (modify — `world_view`, `move`)
- `game/urls.py` (modify — `/play/`, `/play/move/`)

## Requirements
1. `world_view` (`@login_required`): builds the engine `World` via services, renders
   a CSS-grid of cells. Show player `@`, monsters, town, treasure with distinct
   icons/emoji + theme colors. Redirect to character_create if no character.
2. `move` (POST): calls `services.do_move(user, direction)`. Result routing:
   - `moved`/`blocked` → re-render world.
   - `monster` → start combat, redirect to `/combat/`.
   - `town` → redirect to `/town/`.
   - `treasure` → grant reward, mark cleared, flash a message, re-render.
3. Movement controls: 4 D-pad `<form>` buttons (N/S/E/W) that POST — fully functional
   without JS. `keys.js` listens for arrow keys and submits the matching direction
   (progressive enhancement only).
4. Responsive: grid scales to viewport; D-pad usable by thumb on mobile.

## Acceptance Criteria
- [ ] Grid renders with player, monsters, town, treasure visible.
- [ ] D-pad buttons move the player without JS; arrow keys also work.
- [ ] Walking into a monster starts combat; onto town opens town; onto treasure rewards once.

## Existing Code to Reference
- `.ship/plan.md` Section 6 (grid notes)

## Dependencies
- Task 010

## Commit Message
feat(web): world grid view with D-pad and arrow-key movement
