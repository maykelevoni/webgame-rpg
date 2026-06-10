"""Data migration: extend the overworld with two new biomes and link them into a
progression chain off Greenwood. Idempotent and reversible.

World graph after this migration:
    Greenwood (grass, start) --door--> Sunscorch Dunes (desert, ~lvl 2)
    Sunscorch Dunes          --door--> Greenwood            (back)
    Sunscorch Dunes        --portal--> Frostvale (ice, ~lvl 3-4)
    Frostvale              --portal--> Sunscorch Dunes      (back)

Both are remembered overworld areas (stable seed, non-descend), unlike the Old
Mine dungeon. Their biome beasts (scorpion/viper, ice-bear/winter-wolf) were
already seeded in 0017; this only wires up the areas + links.
"""
from django.db import migrations


def seed(apps, schema_editor):
    MapArea = apps.get_model("game", "MapArea")
    MapConnection = apps.get_model("game", "MapConnection")

    greenwood = MapArea.objects.filter(key="greenwood").first()
    dunes, _ = MapArea.objects.update_or_create(
        key="sunscorch-dunes",
        defaults=dict(name="Sunscorch Dunes", biome="desert", seed=33310,
                      size=12, is_start=False))
    frost, _ = MapArea.objects.update_or_create(
        key="frostvale",
        defaults=dict(name="Frostvale", biome="ice", seed=51512,
                      size=12, is_start=False))

    def link(frm, to, kind, label):
        if frm is None or to is None:
            return
        MapConnection.objects.get_or_create(
            from_area=frm, to_area=to, kind=kind,
            defaults=dict(label=label, descend=False))

    link(greenwood, dunes, "door", "Sunscorch Dunes")
    link(dunes, greenwood, "door", "Greenwood")
    link(dunes, frost, "portal", "Frostvale")
    link(frost, dunes, "portal", "Sunscorch Dunes")


def unseed(apps, schema_editor):
    MapArea = apps.get_model("game", "MapArea")
    # Connections cascade-delete with their areas.
    MapArea.objects.filter(key__in=["sunscorch-dunes", "frostvale"]).delete()


class Migration(migrations.Migration):
    dependencies = [("game", "0024_character_vault_gold")]
    operations = [migrations.RunPython(seed, unseed)]
