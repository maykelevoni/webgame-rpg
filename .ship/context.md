# Ship Context Log

## Key Decisions
- **Project:** Rebuild "ez-rpg" — a modular web RPG. Learning project for a Python learner.
- **Stack: Django** (pivoted from Flask). Chosen to get auth + admin + ORM for free,
  and to align with the user's Meta Django certification.
- **Pure-Python engine** (`engine/`) is framework-free and never imports Django. Django
  is a thin shell (models/views/admin/templates). This is the core architecture rule.
- **Database: Neon** (serverless Postgres) via `DATABASE_URL` in `.env`. Django ORM.
- **Auth included now** (Django built-in). Characters have `owner` FK to User.
  Identity seam: `get_current_player(request)` resolves player from `request.user`;
  engine never sees auth.
- **Plugins** stay pure-Python, folder auto-discovered at engine level — NOT Django apps
  (keeps "drop a file to add a feature" simple). Enable/disable state stored in DB, P3.
- **Themes** = CSS folders under static, selectable via dropdown, saved per user.
- **Management UI** = Django admin (no hand-built settings page).
- **World:** single 10×10 grid overworld, step-based server-rendered movement
  (arrow keys + mobile D-pad). Visible, randomly-placed monsters. Town tile opens a
  menu (shop + rest). Treasure tiles. No real-time JS.
- **Progression loop:** fight visible mobs → gold + XP → level up → buy/equip gear in town.

## Constraints
- Code readable + commented for a Python learner.
- Responsive (works on phone).
- Engine must remain importable/testable without Django.

## Notes
- User prefers conversational Q&A over multiple-choice popups.
- Single map for MVP; more maps later, possibly as a plugin.
