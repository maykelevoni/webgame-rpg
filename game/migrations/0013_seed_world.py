"""Data migration: seed the starting world — two connected areas, their links,
biome monster tuning, and a dungeon monster. Also drops existing characters into
the start area. Idempotent and reversible.

World graph (slice 1):
    Greenwood (grass, start) --mine entrance--> Old Mine (dungeon)
    Old Mine  --stairs up--> Greenwood        (back)
    Old Mine  --hole (descend)--> Old Mine     (fresh deeper level)
    Greenwood --to town menu--> (existing /town/, keeps shop + village)
"""
from django.db import migrations


def seed(apps, schema_editor):
    MapArea = apps.get_model("game", "MapArea")
    MapConnection = apps.get_model("game", "MapConnection")
    Monster = apps.get_model("game", "Monster")
    Character = apps.get_model("game", "Character")

    greenwood, _ = MapArea.objects.update_or_create(
        key="greenwood",
        defaults=dict(name="Greenwood", biome="grass", seed=20240611,
                      size=12, is_start=True))
    mine, _ = MapArea.objects.update_or_create(
        key="old-mine",
        defaults=dict(name="Old Mine", biome="dungeon", seed=7777,
                      size=12, is_start=False))

    def link(frm, to, kind, label, descend=False):
        MapConnection.objects.get_or_create(
            from_area=frm, to_area=to, kind=kind,
            defaults=dict(label=label, descend=descend))

    link(greenwood, mine, "mine", "Old Mine")
    link(greenwood, None, "town", "Town")
    link(mine, greenwood, "stairs", "Surface")
    link(mine, mine, "hole", "Deeper", descend=True)

    # Biome tuning + sight radius on the starter monsters; add a dungeon dweller.
    for key, biome, sight in [("slime", "grass", 3), ("goblin", "grass", 4),
                              ("wolf", "grass", 6)]:
        Monster.objects.filter(key=key).update(biome=biome, sight_radius=sight)
    Monster.objects.update_or_create(
        key="skeleton",
        defaults=dict(name="Skeleton", max_hp=16, attack=7, defense=2,
                      gold_reward=12, xp_reward=18, min_level=1,
                      biome="dungeon", sight_radius=5))

    # Existing saves begin in Greenwood, at its centre.
    Character.objects.update(current_area=greenwood,
                             pos_x=greenwood.size // 2, pos_y=greenwood.size // 2)


def unseed(apps, schema_editor):
    MapArea = apps.get_model("game", "MapArea")
    Monster = apps.get_model("game", "Monster")
    Character = apps.get_model("game", "Character")
    Character.objects.update(current_area=None)
    Monster.objects.filter(key="skeleton").delete()
    MapArea.objects.filter(key__in=["greenwood", "old-mine"]).delete()


class Migration(migrations.Migration):
    dependencies = [("game", "0012_maparea_character_area_state_monster_biome_and_more")]
    operations = [migrations.RunPython(seed, unseed)]
