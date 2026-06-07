# ez-rpg

A modular, web-based RPG built with **Django** over a **pure-Python game engine**.
Walk a grid world, fight monsters turn-by-turn, earn gold and XP, level up, and
buy/equip gear in town. Everything is **modular**: add features with **plugins**
and restyle the whole UI with **themes**.

> Learning project. The architecture keeps the game logic (`engine/`) completely
> separate from the web framework, so the code is easy to follow and the engine
> is testable on its own.

## Architecture (the one rule)

**`engine/` never imports Django.** It is plain Python.

```
HTTP -> game/views.py -> game/services.py -> engine/   (the game rules)
                              |
                         game/models.py -> Neon Postgres (all data + balance)
```

- `engine/` — pure-Python game: character, items, combat, world grid, leveling,
  plus the plugin loader and theme registry.
- `game/` — the thin Django shell: models (Neon), views, admin, templates.
- `plugins/` — drop-in Python plugins, auto-discovered. Core game = code; plugins extend it.
- All data **and balance numbers** (items, monsters, starting stats, XP curve…)
  live in the database and are editable in the Django admin.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit .env
# Put your Neon connection string in DATABASE_URL (leave blank to use local sqlite)
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Run tests with:

```bash
pytest
```

## More docs

How to write a plugin and how to add a theme are documented later in this file
as those systems are built.
