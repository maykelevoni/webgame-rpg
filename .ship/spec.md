# webgame-rpg — Feature Specification

## Feature Summary
A modular web-based RPG built with Django. Players sign up / log in, create a
character, explore a grid overworld to find and fight monsters, earn gold and
XP, level up, buy and equip gear in town, and save their progress to a Neon
Postgres database.

Django is chosen to get auth, an admin panel, and an ORM "for free" — directly
serving the login and plugin/theme-management needs, and matching the Meta
certification curriculum the user is studying.

The project is "modular" in two ways:
- **Plugins** — drop a Python file into a `plugins/` folder to add new game
  features/actions. Auto-discovered at startup.
- **Themes** — pick a theme from a dropdown to restyle the whole UI (swap CSS).

## Problem Statement / Goal
Rebuild the user's old "webgame-rpg" concept with modern Python as a **learning
project**. Code must be readable and well-commented for someone learning Python.
The game engine is pure, framework-free Python; Django is a thin shell on top.
This keeps the engine fully testable and insulates the core game from the web
framework, while leveraging Django's batteries (auth, admin, ORM) — and aligning
the project with the user's Meta Django certification.

## Architecture (decided)
```
engine/              Pure Python game rules. No Django, no DB. Fully testable.
                     (Character, combat, inventory, world/grid, leveling,
                      plugin loader, theme registry)
ezrpg/  (Django)     The thin web shell:
  config/            settings.py (Neon via DATABASE_URL), urls.py, wsgi
  game/  (app)       models.py  — persists engine data to Neon (owner = User FK)
                     views.py   — call engine, render templates
                     admin.py   — register models => free admin/management UI
                     templates/ — Jinja-like Django templates
                     static/themes/ — theme CSS folders
plugins/             Pure-Python drop-in plugins, auto-discovered at engine level
                     (NOT Django apps — keeps "drop a file to add a feature" simple).
```
Design rule: the engine never imports Django. Django handles auth, admin, ORM,
routing; the engine handles the game and its plugin/theme system.

## Tech Stack
- Python + Django (web shell: auth, admin, ORM, routing, templates)
- Django ORM → Neon serverless Postgres (psycopg driver)
- `.env` holds `DATABASE_URL` (never committed); loaded via dj-database-url / django-environ
- Django templates + CSS theme folders; minimal JS (server-rendered, step-based movement)
- pytest (pytest-django) for engine + view tests

## User Stories & Acceptance Criteria

### Character & Progression
- **Create a character** (C1): name + starting stats (HP, Attack, Defense).
  - AC: form to enter a name; character starts with sensible base stats, level 1, 0 XP, starting gold.
- **Character sheet** (C2): view stats, level, XP, gold, equipped gear.
  - AC: a page shows current stats including bonuses from equipped gear.
- **Leveling up** (C4): gain XP from winning fights; enough XP raises level and stats.
  - AC: XP accumulates; crossing a threshold increases level and base stats; surplus XP carries over.
- **Equip gear** (C6): items (weapon, armor) that modify stats when equipped.
  - AC: equipping a weapon/armor changes effective Attack/Defense; can swap/unequip.

### Combat
- **Turn-based combat** (B1): fight one visible monster; Attack deals damage, enemy retaliates.
  - AC: turns alternate; damage uses Attack vs Defense; win when enemy HP ≤ 0, lose when player HP ≤ 0.
- **Use item in combat** (B2): use a consumable (e.g. healing potion) on your turn.
  - AC: using a potion restores HP and consumes the item; counts as the player's turn.
- **Flee** (small, supports usability): leave a fight and return to the map.
  - AC: fleeing ends combat without rewards and returns the player to their map tile.
- **Rewards**: winning grants gold + XP (and possibly an item drop).
  - AC: on victory, player gains defined gold and XP.

### Inventory & Economy
- **Inventory** (I1): hold items (consumables + gear).
  - AC: items are listed; quantities tracked for stackables.
- **Use/consume item** (I2): use a consumable outside combat too.
  - AC: using a potion outside combat heals and consumes it.
- **Gold** (I3): currency earned from fights/treasure.
  - AC: gold balance shown and updated on earn/spend.
- **Shop** (I4): in town, buy and sell items/gear with gold.
  - AC: buying deducts gold and adds the item; selling adds gold and removes the item.

### World & Exploration
- **Grid overworld** (W2): a 10×10 tile map. Player moves one tile per action
  (arrow keys on desktop, on-screen D-pad / tap on mobile). Movement is
  server-rendered and step-based (no real-time JS loop).
  - AC: player can move N/S/E/W within bounds; walls/obstacles block movement.
- **Visible, randomly-placed monsters**: monsters are placed on random tiles and
  shown on the map; walking into one starts combat.
  - AC: several monsters visible at random positions; stepping onto a monster tile starts a fight; defeated monsters are removed.
- **Town tile**: stepping onto the town tile opens a **menu** (no walking inside):
  Shop, Rest/Heal, Leave.
  - AC: town menu offers shop access and a rest action that restores HP.
- **Treasure tiles**: random tiles grant gold or an item when stepped on.
  - AC: stepping on treasure grants a reward once, then the tile is emptied.

### Plugin System
- **Auto-discovery** (P1): plugins in `plugins/` are loaded at startup.
  - AC: adding a valid plugin file makes its feature available without editing core code.
- **Register a feature** (P2): a plugin can register a new action/feature via a defined interface.
  - AC: a documented base class / register hook; engine exposes registered actions.
- **Example plugin** (P4): ship one working example plugin demonstrating the system.
  - AC: one example plugin is present, enabled, and visibly affects the game.
- **Plugin guide** (P6 / part of README): a short "how to write a plugin" with a template.
  - AC: README section + a commented template plugin file.

### Theme System
- **Theme switcher** (T1): pick a theme from a dropdown → whole UI restyles.
  - AC: selecting a theme changes the active CSS site-wide; choice saved per user.
- **Themes are CSS folders** (T3): each theme is a folder; adding one is drop-in.
  - AC: a new theme folder appears in the dropdown automatically.
- **Two example themes** (T2 + T4): ship "Dark Fantasy" and a contrasting "Light Parchment" to prove swapping works.
  - AC: both themes selectable and visually distinct.

### Management / Admin
- **Django admin** (replaces a custom settings page): registered models give a
  free management UI for characters, items, and plugin enable/disable state.
  - AC: a superuser can log into `/admin` and view/edit characters, items, and toggle plugins.
- **Plugin toggle** (P3): plugins can be enabled/disabled (stored in DB), surfaced in admin.
  - AC: disabling a plugin in admin removes its feature from the game without deleting files.

### Accounts & Identity
- **Sign up / log in** (D5): players register and log in using Django's built-in auth.
  - AC: a visitor can sign up, log in, log out; characters belong to the logged-in user.
- **Identity seam**: a single `get_current_player(request)` helper resolves the
  active player from `request.user`. The engine never sees auth — it only receives
  a character object. (Designed so the rule "engine knows nothing about login" holds.)

### Persistence (Neon)
- **Save character + inventory** (D1, D2): persisted to Neon Postgres via Django ORM.
  - AC: character stats, level, XP, gold, inventory, and equipped gear are saved; each
    character has an `owner` FK to the Django User.
- **Load on return** (D3): logging back in loads the saved character.
  - AC: restarting the server and logging in restores the saved character state.

### Web / UX
- **Home page** (U1): start a new game or continue an existing save.
  - AC: landing page links to create-character and continue.
- **Responsive** (U2): playable on phone and desktop.
  - AC: grid, combat, shop, and menus are usable on a small screen; mobile D-pad for movement.

### Learning niceties
- **Commented code** (L1) and **README with architecture** (L2).
- **Engine tests** (L3, pytest) for combat/leveling/inventory core logic.

## Out of Scope (MVP)
- Multiple maps/zones (single 10×10 map for now; more later, possibly via plugin)
- Real-time / tile-map JavaScript engine (movement is step-based, server-rendered)
- Character classes (C5), special abilities (B5), combat history persistence (D4)
- Multiplayer / social / PvP features
- Password reset emails, social login (basic username/password auth only for MVP)
- A hand-built custom admin (we use Django's built-in admin instead)

## Success Criteria
A player can: open the app → sign up / log in → create a character → walk a
10×10 grid → fight a visible monster turn-by-turn → use a potion → win for gold
+ XP → level up → enter town → buy and equip gear → log out and back in to find
their save intact (Neon) → switch themes → and the whole thing works on a phone.
A superuser can manage characters/items/plugins via Django admin. One example
plugin and two themes demonstrate the modular system, and a README explains how
to add more.
