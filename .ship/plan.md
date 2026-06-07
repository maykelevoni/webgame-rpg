# ez-rpg — Technical Plan

> Greenfield project. Django shell over a pure-Python engine, Neon Postgres.
> Golden rule: **`engine/` never imports Django.** The bridge lives in `game/services.py`.

---

## Section 1: Architecture Integration

Three layers, one strict dependency direction (web → engine, never the reverse):

```
                 HTTP
                  │
   game/views.py  │  (thin: parse request, call services, render)
        │
   game/services.py   ← THE BRIDGE: load engine objects from DB models,
        │                run engine logic, save results back to DB
   ┌────┴─────────────────────────┐
   │                              │
engine/  (pure Python)      game/models.py (Django ORM ↔ Neon)
```

- **engine/** = the game. Knows nothing about Django, requests, or the DB. Pure
  classes + functions, unit-testable in isolation.
- **game/models.py** = how engine state is *stored* (Django models on Neon).
- **game/services.py** = the only place that translates between a DB row and an
  engine object. Views stay thin; the engine stays pure.

Patterns to follow throughout (for the learner):
- Engine objects are plain Python classes with clear methods (`character.gain_xp(20)`).
- Views never contain game rules — they call `services` which call the engine.
- Every engine module gets a docstring + inline comments explaining the "why".

---

## Section 2: Database Changes (Django models on Neon)

All models in `game/models.py`. Migrations via `manage.py makemigrations/migrate`.

### `Profile` (one per user — holds non-game prefs)
| field | type | notes |
|-------|------|-------|
| user | OneToOne(User) | Django auth user |
| theme | CharField(default="dark-fantasy") | selected theme folder name |

### `Character` (the persisted game state)
| field | type | notes |
|-------|------|-------|
| owner | FK(User) | identity seam target |
| name | CharField | |
| level | PositiveInt (default 1) | |
| xp | PositiveInt (default 0) | |
| max_hp / hp | PositiveInt | current + max |
| base_attack / base_defense | PositiveInt | before gear bonuses |
| gold | PositiveInt (default 0) | |
| map_seed | BigInt | deterministic 10×10 generation |
| pos_x / pos_y | PositiveInt | position on the grid |
| cleared | JSONField (default list) | defeated monster / opened treasure coords |
| created_at / updated_at | DateTime | |

### `Item` (the item catalog — admin-editable)
| field | type | notes |
|-------|------|-------|
| key | SlugField (unique) | stable id (e.g. "potion", "iron-sword") |
| name | CharField | display name |
| kind | CharField (choices: consumable/weapon/armor) | |
| price | PositiveInt | shop price |
| heal | PositiveInt (default 0) | for consumables |
| attack_bonus | PositiveInt (default 0) | for weapons |
| defense_bonus | PositiveInt (default 0) | for armor |
| sellable | Bool (default True) | |

### `Monster` (the base spawn table — admin-editable)
| field | type | notes |
|-------|------|-------|
| key | SlugField (unique) | |
| name | CharField | |
| max_hp / attack / defense | PositiveInt | |
| gold_reward / xp_reward | PositiveInt | granted on defeat |
| min_level | PositiveInt (default 1) | gates where it can spawn |

### `InventoryItem` (a stack a character owns)
| field | type | notes |
|-------|------|-------|
| character | FK(Character) | |
| item | FK(Item) | the catalog row |
| quantity | PositiveInt (default 1) | |
| equipped | Bool (default False) | for gear |
| slot | CharField(null) | "weapon" / "armor" when equipped |

### `PluginState` (P3 — enable/disable, managed in admin)
| field | type | notes |
|-------|------|-------|
| name | CharField (unique) | plugin module name |
| enabled | Bool (default True) | |

### `GameConfig` (singleton — all balance knobs, admin-editable)
One row only (enforced). Holds every tunable number so nothing is hardcoded:
| field | type | default | notes |
|-------|------|---------|-------|
| start_hp | PositiveInt | 30 | new character HP |
| start_attack | PositiveInt | 8 | new character attack |
| start_defense | PositiveInt | 4 | new character defense |
| start_gold | PositiveInt | 20 | new character gold |
| grid_size | PositiveInt | 10 | world is grid_size × grid_size |
| monster_count | PositiveInt | 6 | monsters placed per map |
| treasure_count | PositiveInt | 3 | treasure tiles per map |
| xp_base | PositiveInt | 50 | XP needed for level 2 |
| xp_growth | Float | 1.5 | curve multiplier per level |
| stat_growth | PositiveInt | 3 | stat points gained per level |
| rest_cost | PositiveInt | 10 | gold to rest/heal in town |
| treasure_gold_min / max | PositiveInt | 5 / 25 | treasure reward range |

`GameConfig.load()` returns the single row (creating defaults if missing). The
engine receives these values as inputs — see Section 4.

**Everything-in-DB decision:** the item catalog and base monster spawn table are
**Django models** (`Item`, `Monster`), so they're editable in the admin. A data
migration **seeds** the starting items (potion, iron sword, leather armor),
monsters (e.g. goblin, slime, wolf), and the default `GameConfig` row so the game
is playable out of the box.
The pure engine still never touches the DB — see Section 4: the bridge loads these
rows and passes them to the engine as plain data objects.

---

## Section 3: Engine Design (pure Python, `engine/`)

| file | responsibility |
|------|----------------|
| `engine/character.py` | `Character` class: stats, `effective_attack/defense()` (base + gear), `take_damage`, `heal`, `gain_xp` (handles level-up), inventory ops, equip/unequip |
| `engine/items.py` | `Item` dataclass (key, name, kind, price, heal, attack_bonus, defense_bonus) — the *shape/behavior* of an item. No hardcoded catalog data; the catalog comes from the DB via the bridge as `Item` instances |
| `engine/leveling.py` | `xp_to_next(level)` thresholds + stat growth on level up |
| `engine/monsters.py` | `Monster` dataclass (key, name, hp, atk, def, gold/xp reward, min_level) + spawn-selection helpers that operate on a *provided* list of monsters (the list comes from the DB; plugins may append more) |
| `engine/combat.py` | `Combat` class: `player_attack()`, `enemy_turn()`, `use_item(key)`, `flee()`; returns turn log + outcome (win/lose/fled). Win → rewards |
| `engine/world.py` | `World` (10×10): deterministic generation from `map_seed`, places town tile, monsters, treasure (skipping `cleared`). `move(direction)` → result enum (`moved`/`blocked`/`monster`/`town`/`treasure`) |
| `engine/plugins.py` | `PluginBase` + `PluginRegistry` + `load_plugins(enabled_names)`: scans `plugins/`, imports modules, calls each plugin's `register(registry)`. Extension points: add monsters, add items, add town actions, `on_victory(character)` hook |
| `engine/themes.py` | `available_themes()` — scans the themes static folder, returns folder names |
| `engine/__init__.py` | small façade exporting the public classes |

Engine has **no DB and no I/O** except `plugins.py`/`themes.py` reading the
filesystem (loading plugin modules and listing theme folders).

---

## Section 4: The Bridge (`game/services.py`)

Functions that views call. Each loads engine objects, runs logic, persists.
The bridge is also where **DB rows become engine data**:

- `load_config()` → reads the `GameConfig` singleton → a plain config object the
  engine uses for starting stats, grid size, spawn counts, XP curve, rest cost, etc.
- `load_catalog()` → reads `Item` rows → dict of engine `Item` objects (`{key: Item}`).
- `load_spawn_table()` → reads `Monster` rows (+ enabled-plugin monsters) → list of engine `Monster`.
- `get_or_create_character(user, name=None)` → builds/loads a `Character` engine
  object from the `Character` model + its `InventoryItem` rows (resolved via the catalog).
- `save_character(engine_char, model)` → writes engine state back to DB.
- `load_world(character_model)` → builds engine `World` from `map_seed` + `cleared`,
  using the spawn table.
- `do_move(user, direction)` → move, persist new pos / handle tile result.
- `start_combat / combat_action(user, action, payload)` → run a `Combat` turn,
  persist HP/rewards/cleared on win; apply enabled-plugin `on_victory` hooks.
- `buy_item / sell_item / equip_item / use_item / rest(user, ...)`.
- `get_active_plugins()` → reads `PluginState`, returns enabled plugin registry.

Principle: the engine receives catalog/monsters as **plain Python objects**; it
never imports models or runs queries. All DB access is here in `services.py`.

`game/identity.py`: `get_current_player(request)` → resolves the `Character` for
`request.user`. The single seam between auth and the game.

---

## Section 5: Routes / Views (`game/urls.py` + `game/views.py`)

All game routes require login (`@login_required`); auth routes are public.

| method | path | view | purpose |
|--------|------|------|---------|
| GET | `/` | `home` | landing: continue or create character |
| GET/POST | `/accounts/signup/` | `signup` | register (Django auth handles login/logout) |
| GET/POST | `/accounts/login/` | Django auth | login |
| POST | `/accounts/logout/` | Django auth | logout |
| GET/POST | `/character/create/` | `character_create` | name a new character |
| GET | `/character/` | `character_sheet` | stats, gold, equipped gear |
| GET | `/play/` | `world_view` | render the 10×10 grid |
| POST | `/play/move/` | `move` | N/S/E/W → re-render / route to encounter |
| GET | `/combat/` | `combat_view` | current battle screen |
| POST | `/combat/action/` | `combat_action` | attack / use item / flee |
| GET | `/town/` | `town_view` | town menu (shop, rest, leave) |
| GET/POST | `/town/shop/` | `shop_view` | buy/sell items + gear |
| POST | `/town/rest/` | `rest` | restore HP |
| POST | `/character/equip/` | `equip` | equip/unequip gear |
| POST | `/character/use-item/` | `use_item` | use a consumable outside combat |
| POST | `/settings/theme/` | `set_theme` | save selected theme to Profile |
| — | `/admin/` | Django admin | manage characters/items/plugins (superuser) |

---

## Section 6: Frontend / Templates (`game/templates/`)

- `base.html` — links the **active theme's CSS** (`static/themes/<theme>/theme.css`),
  top nav, the **theme dropdown** (posts to `/settings/theme/`), `{% block content %}`.
- `game/context_processors.py` — injects `active_theme` + `available_themes` into
  every template so the dropdown and CSS link work site-wide.
- Pages: `home.html`, `registration/login.html`, `registration/signup.html`,
  `character_create.html`, `character_sheet.html`, `world.html`, `combat.html`,
  `town.html`, `shop.html`.
- **Grid (`world.html`)**: a CSS-grid of 10×10 cells (emoji/icon per tile). Movement
  via a **D-pad of buttons** (POST direction) that works with zero JS; a tiny
  progressive-enhancement script submits on arrow-key press for desktop. Mobile-first,
  responsive (CSS grid + flexible cell sizing).
- Combat/shop/town are simple forms + lists — easy to theme, responsive by default.

### Themes (CSS folders)
- `static/themes/dark-fantasy/theme.css`
- `static/themes/light-parchment/theme.css`
- Each defines the same CSS variables / classes (`--bg`, `--panel`, `--accent`,
  tile colors). Adding a folder = new option in the dropdown automatically.

---

## Section 7: Plugin System (the demo of "modular")

- `engine/plugins.py` exposes a `PluginBase` (or simple `register(registry)` hook).
- `PluginRegistry` extension points for MVP:
  - `add_monster(monster)` — inject into spawn table
  - `add_item(key, item)` — add to the catalog/shop
  - `add_town_action(name, handler)` — new button in town
  - `on_victory(fn)` — callback after winning a fight (gets the character)
- Loader reads enabled set from `PluginState`, imports each `plugins/*.py`, calls
  `register(registry)`.
- **Ship one example plugin**: `plugins/healing_shrine.py` — adds a "Pray at Shrine"
  **town action** that heals for a small gold cost. Clearly visible proof the system
  works (a new button appears in town only when the plugin is enabled).
- **Ship a template**: `plugins/_template_plugin.py.txt` — heavily commented, shows
  every hook. README documents "how to write a plugin".

---

## Section 8: Service / External Integration

- **Neon Postgres** — only external service. Connection via `DATABASE_URL` in `.env`
  (loaded with `python-dotenv`), parsed by `dj-database-url`. `.env` is gitignored;
  ship `.env.example`. User supplies the real connection string.
- No other external APIs.

---

## Section 9: File Map

**Create:**
```
manage.py
requirements.txt
.env.example
.gitignore
README.md                         # architecture + how to add plugins/themes

config/__init__.py
config/settings.py                # apps, Neon DB, static, auth redirects, templates
config/urls.py
config/wsgi.py

engine/__init__.py
engine/character.py
engine/items.py
engine/leveling.py
engine/monsters.py
engine/combat.py
engine/world.py
engine/plugins.py
engine/themes.py

game/__init__.py
game/apps.py
game/models.py
game/admin.py
game/identity.py
game/services.py
game/views.py
game/urls.py
game/context_processors.py
game/templates/base.html
game/templates/home.html
game/templates/registration/login.html
game/templates/registration/signup.html
game/templates/character_create.html
game/templates/character_sheet.html
game/templates/world.html
game/templates/combat.html
game/templates/town.html
game/templates/shop.html
game/static/themes/dark-fantasy/theme.css
game/static/themes/light-parchment/theme.css
game/static/js/keys.js            # tiny arrow-key → submit enhancement

plugins/__init__.py
plugins/healing_shrine.py         # example plugin
plugins/_template_plugin.py.txt   # documented template

tests/test_character.py
tests/test_combat.py
tests/test_world.py
tests/test_leveling.py
```

**Dependencies (`requirements.txt`):** django, dj-database-url, psycopg[binary],
python-dotenv, pytest, pytest-django.

---

## Build order (feeds Phase 3 breakdown)
1. Project scaffold + settings + Neon connection + .env + requirements
2. Engine: character, items, leveling (+ tests)
3. Engine: monsters, combat (+ tests)
4. Engine: world grid + movement (+ tests)
5. Django models + migrations + admin + **data migration seeding Items & Monsters**
6. Bridge services + identity seam
7. Auth (signup/login/logout) + base template + theme system
8. Home + character create + character sheet
9. World view + movement UI (D-pad + arrow keys, responsive)
10. Combat views + town + shop + rest + equip
11. Plugin system + example plugin + template + theme #2
12. README + polish + responsive pass
```
