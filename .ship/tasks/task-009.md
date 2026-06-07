# Task 009: Auth + base template + theme system

## Type
ui

## Description
User signup/login/logout, the site-wide base template that loads the active
theme's CSS and shows the theme dropdown, and the two example themes.

## Files
- `game/templates/base.html` (create)
- `game/templates/registration/login.html` (create)
- `game/templates/registration/signup.html` (create)
- `game/views.py` (create — `signup`, `set_theme`)
- `game/urls.py` (create — auth + theme routes)
- `game/context_processors.py` (create)
- `game/static/themes/dark-fantasy/theme.css` (create)
- `game/static/themes/light-parchment/theme.css` (create)

## Requirements
1. Use Django's built-in auth views for login/logout; a `signup` view using
   `UserCreationForm` that logs the user in and redirects to `/play/`.
2. `base.html`: links `static/themes/<active_theme>/theme.css`, a top nav (login state
   aware), and a theme `<select>` that POSTs to `/settings/theme/`. `{% block content %}`.
3. `context_processors.py`: inject `active_theme` (from Profile, default dark-fantasy)
   and `available_themes` (from `engine.themes.available_themes`). Register it in settings.
4. `set_theme` view saves the chosen theme to the user's `Profile`.
5. Two themes define the SAME CSS variables/classes (`--bg`, `--panel`, `--text`,
   `--accent`, tile colors, buttons) with clearly different palettes. Mobile-first.
6. Register `game.urls` in `config/urls.py`; add `accounts/` auth includes.

## Acceptance Criteria
- [ ] Can sign up, log in, log out.
- [ ] Selecting a theme restyles the whole site and persists across pages/sessions.
- [ ] Both themes look distinct; layout is responsive on a narrow viewport.

## Existing Code to Reference
- `.ship/plan.md` Sections 5 & 6

## Dependencies
- Task 008

## Commit Message
feat(web): auth, base layout, and switchable themes
