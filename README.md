# ez-rpg

A modular, web-based RPG built with **Django** over a **pure-Python game engine**.
Explore a grid world, fight monsters turn-by-turn, earn gold and XP, level up, and
buy/equip gear in town. Everything is **modular**: add features with **plugins**
and restyle the whole UI with **themes**.

> A learning project. The architecture keeps the game logic (`engine/`) completely
> separate from the web framework, so the code is easy to follow and the engine is
> testable on its own.

## The core idea — engine vs. Django

**The one rule: `engine/` never imports Django.** It's plain Python.

```
HTTP -> game/views.py -> game/services.py -> engine/   (the game rules)
                              |
                         game/models.py -> Neon Postgres  (all data + balance)
```

- **`engine/`** — the game itself: `character`, `items`, `leveling`, `monsters`,
  `combat`, `world` (the grid), plus `plugins` (the plugin loader) and `themes`.
  Pure Python, no database — covered by tests in `tests/`.
- **`game/`** — the thin Django shell: `models.py` (Neon), `views.py`, `admin.py`,
  templates, and `services.py` — the **only** place that turns database rows into
  engine objects and back.
- **`plugins/`** — drop-in Python files that add features. The core game is *not*
  made of plugins; plugins extend it through hooks.
- **All data and balance** (items, monsters, starting stats, the XP curve, rewards…)
  live in the database and are editable in the Django admin — nothing is hardcoded.

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure the database
cp .env.example .env
#   Edit .env and paste your Neon connection string into DATABASE_URL.
#   Get it from: Neon dashboard -> your project -> "Connection string".
#   (Leave DATABASE_URL blank to use a local sqlite file instead.)

# 4. Create the tables and seed starter content (items, monsters, config)
python manage.py migrate

# 5. Create an admin account (for the /admin panel)
python manage.py createsuperuser

# 6. Run it
python manage.py runserver
```

Then open http://127.0.0.1:8000/ , sign up, and play. The admin panel is at
http://127.0.0.1:8000/admin/ .

Run the tests with:

```bash
pytest
```

## Managing the game (no code needed)

Log into `/admin` as your superuser to:
- **Items** — add/edit shop items (price, heal, attack/defense bonuses).
- **Monsters** — tune enemy stats, rewards, and the level they appear at.
- **Game config** — the single row of balance knobs: starting stats, grid size,
  number of monsters/treasure, the XP curve, rest cost, treasure rewards.
- **Plugin states** — turn plugins on/off.
- **Characters** — inspect or edit any player's character.

## How to write a plugin

A plugin is a Python file in `plugins/` that defines `register(registry)`.

1. Copy `plugins/_template_plugin.py.txt` to `plugins/my_plugin.py`.
2. Keep the hooks you want, delete the rest. Available hooks:
   - `registry.add_monster(monster)` — add an enemy to the spawn table
   - `registry.add_item(item)` — add an item to the catalog
   - `registry.add_town_action(label, handler)` — add a button to the town menu
   - `registry.on_victory(fn)` — run code after the player wins a fight
3. Restart the server. The plugin is auto-discovered and a toggle appears in the
   admin under **Plugin states** (enabled by default).

See `plugins/healing_shrine.py` for a complete working example (it adds a
"Pray at Shrine" town action).

## How to add a theme

A theme is a folder containing a `theme.css` file.

1. Create `game/static/themes/<your-theme>/theme.css`.
2. Define the colour variables (copy an existing theme as a starting point):
   `--bg`, `--panel`, `--text`, `--muted`, `--border`, `--accent`, `--accent-2`,
   `--accent-text`, and the tile colours `--tile-empty/town/monster/treasure`,
   `--player`.
3. It appears in the theme dropdown automatically. Layout lives in
   `game/static/css/base.css` — themes only change colours.

## Where to next (it's already Django!)

This project was built directly in Django to get auth, the admin panel, and the
ORM for free — the same stack the Meta certification teaches. The engine being
framework-free means you could put a different web layer in front of it later, but
you don't need to: the Django shell is the real thing.
