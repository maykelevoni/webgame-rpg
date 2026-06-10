"""Data migration: the visual/theming pass.

- Give every building and monster a readable **emoji** (the Kenney tiles were hard to
  read); rename **Quarry → Stonecutter** and **Hospital → Mead Hall** to match the
  castle/village direction (`docs/IMPLEMENTATION-STATUS.md`).
- Add a roster of new **beasts** (real animals + Norse creatures) with biome + stats,
  so the maps spawn more than slime/goblin/wolf/skeleton.

Idempotent (update_or_create / field updates) and reversible.
"""
from django.db import migrations

# key -> (emoji, optional new name). None name = keep existing.
BUILDING_EMOJI = {
    "longhouse":   ("🛖", None),
    "lumber-camp": ("🪓", None),
    "quarry":      ("🧱", "Stonecutter"),
    "farm":        ("🐄", None),
    "storehouse":  ("📦", None),
    "market":      ("🏪", None),
    "hospital":    ("🍺", "Mead Hall"),
}

MONSTER_EMOJI = {
    "slime": "🟢", "goblin": "👺", "wolf": "🐺", "skeleton": "💀", "bandit": "🗡️",
}

# New beasts: key, name, emoji, max_hp, atk, def, gold, xp, min_level, biome, sight
BEASTS = [
    # forest / grass
    ("boar",      "Wild Boar",   "🐗", 18,  6, 2, 10, 14, 1, "grass",   4),
    ("bear",      "Brown Bear",  "🐻", 34, 11, 4, 22, 30, 3, "grass",   5),
    ("spider",    "Forest Spider","🕷️", 14,  7, 1,  9, 13, 2, "grass",   5),
    ("stag",      "Great Stag",  "🦌", 22,  6, 3, 14, 18, 2, "grass",   6),
    # desert / sand
    ("scorpion",  "Sand Scorpion","🦂", 16,  9, 2, 12, 16, 2, "desert",  4),
    ("viper",     "Sand Viper",  "🐍", 13, 10, 1, 11, 15, 2, "desert",  5),
    # ice
    ("ice-bear",  "Ice Bear",    "🐻‍❄️", 40, 13, 5, 28, 36, 4, "ice",     5),
    ("winter-wolf","Winter Wolf","🐺", 24,  9, 3, 16, 20, 3, "ice",     7),
    # dungeon / mine
    ("bat",       "Cave Bat",    "🦇", 10,  5, 0,  6,  9, 1, "dungeon", 5),
    ("rat",       "Giant Rat",   "🐀", 12,  5, 1,  7, 10, 1, "dungeon", 4),
    ("troll",     "Cave Troll",  "🧌", 48, 14, 6, 40, 50, 5, "dungeon", 4),
    ("draug",     "Draug",       "👻", 20,  9, 3, 18, 24, 3, "dungeon", 5),
    ("jotunn",    "Jötunn",      "👹", 70, 18, 8, 60, 80, 7, "dungeon", 5),
    ("wyrm",      "Cave Wyrm",   "🐉", 120, 24, 10, 150, 200, 9, "dungeon", 6),
]


def seed(apps, schema_editor):
    BuildingType = apps.get_model("game", "BuildingType")
    Monster = apps.get_model("game", "Monster")

    for key, (emoji, new_name) in BUILDING_EMOJI.items():
        bt = BuildingType.objects.filter(key=key).first()
        if not bt:
            continue
        bt.emoji = emoji
        if new_name:
            bt.name = new_name
        bt.save()

    for key, emoji in MONSTER_EMOJI.items():
        Monster.objects.filter(key=key).update(emoji=emoji)

    for (key, name, emoji, hp, atk, df, gold, xp, lvl, biome, sight) in BEASTS:
        Monster.objects.update_or_create(
            key=key,
            defaults=dict(name=name, emoji=emoji, max_hp=hp, attack=atk,
                          defense=df, gold_reward=gold, xp_reward=xp,
                          min_level=lvl, biome=biome, sight_radius=sight),
        )


def unseed(apps, schema_editor):
    BuildingType = apps.get_model("game", "BuildingType")
    Monster = apps.get_model("game", "Monster")
    # Restore the renamed buildings; drop emoji.
    BuildingType.objects.filter(key="quarry").update(name="Quarry")
    BuildingType.objects.filter(key="hospital").update(name="Hospital")
    BuildingType.objects.filter(key__in=BUILDING_EMOJI).update(emoji="")
    Monster.objects.filter(key__in=MONSTER_EMOJI).update(emoji="")
    Monster.objects.filter(key__in=[b[0] for b in BEASTS]).delete()


class Migration(migrations.Migration):
    dependencies = [("game", "0016_buildingtype_emoji_monster_emoji")]
    operations = [migrations.RunPython(seed, unseed)]
