"""Data migration: seed the starter items, monsters, and the balance config.

This makes the game playable the moment you run `migrate` — there's a shop full of
items, monsters to fight, and a tuning config. Everything is editable afterwards in
the admin. The seed is idempotent (update_or_create) and reversible.
"""
from django.db import migrations

ITEMS = [
    # key, name, kind, price, heal, atk, def, sellable
    ("potion", "Healing Potion", "consumable", 10, 20, 0, 0, True),
    ("iron-sword", "Iron Sword", "weapon", 40, 0, 5, 0, True),
    ("leather-armor", "Leather Armor", "armor", 35, 0, 0, 3, True),
]

MONSTERS = [
    # key, name, hp, atk, def, gold, xp, min_level
    ("slime", "Slime", 8, 3, 0, 5, 8, 1),
    ("goblin", "Goblin", 12, 5, 1, 8, 12, 1),
    ("wolf", "Wolf", 18, 8, 2, 14, 20, 2),
]


def seed(apps, schema_editor):
    Item = apps.get_model("game", "Item")
    Monster = apps.get_model("game", "Monster")
    GameConfig = apps.get_model("game", "GameConfig")

    for key, name, kind, price, heal, atk, dfn, sellable in ITEMS:
        Item.objects.update_or_create(
            key=key,
            defaults=dict(name=name, kind=kind, price=price, heal=heal,
                          attack_bonus=atk, defense_bonus=dfn, sellable=sellable),
        )

    for key, name, hp, atk, dfn, gold, xp, min_level in MONSTERS:
        Monster.objects.update_or_create(
            key=key,
            defaults=dict(name=name, max_hp=hp, attack=atk, defense=dfn,
                          gold_reward=gold, xp_reward=xp, min_level=min_level),
        )

    GameConfig.objects.get_or_create(pk=1)


def unseed(apps, schema_editor):
    Item = apps.get_model("game", "Item")
    Monster = apps.get_model("game", "Monster")
    Item.objects.filter(key__in=[i[0] for i in ITEMS]).delete()
    Monster.objects.filter(key__in=[m[0] for m in MONSTERS]).delete()


class Migration(migrations.Migration):
    dependencies = [("game", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
