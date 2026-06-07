# Task 014: README, learner docs, responsive polish

## Type
ui

## Description
Write the README that explains the architecture and how to add plugins/themes,
and do a final responsive/theming pass across all pages.

## Files
- `README.md` (modify — full docs)
- `game/static/themes/dark-fantasy/theme.css` (modify — polish)
- `game/static/themes/light-parchment/theme.css` (modify — polish)
- `game/templates/base.html` (modify — responsive nav if needed)

## Requirements
1. README sections: project overview; the engine-vs-Django architecture rule
   (engine never imports Django); setup (create venv, install, set `DATABASE_URL`
   from Neon, migrate, createsuperuser, runserver); how the DB holds all data/balance
   (Item/Monster/GameConfig editable in admin); **How to write a plugin** (copy the
   template, drop in `plugins/`, enable in admin); **How to add a theme** (new folder
   with `theme.css` defining the CSS variables); the Django→already-Django note about
   the Meta cert; and a pointer to run tests with `pytest`.
2. Responsive pass: verify grid, combat, shop, town, and sheet are usable at ~360px
   width; nav collapses gracefully; tap targets are large enough.
3. Ensure both themes cover every component consistently.

## Acceptance Criteria
- [ ] README lets a newcomer set up Neon + run the app from scratch.
- [ ] "Add a plugin" and "Add a theme" steps are clear and accurate.
- [ ] All pages are usable and look right on a phone-width viewport in both themes.

## Dependencies
- Task 013

## Commit Message
docs: README, plugin/theme guides, and responsive polish
