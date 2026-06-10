"""Data migration: seed the slice-1 village building catalog.

Gives every new village something to build the moment you run `migrate`. All of
these are editable afterwards in the admin (costs, times, production, icons).
The seed is idempotent (update_or_create) and reversible.

Icons are placeholder sprite names from the Kenney pack — swap them in the admin
to taste; the village UI also labels each tile by name, so the game is readable
even before the art is dialled in.
"""
from django.db import migrations

# key, name, category, fw, fh, cost_wood, cost_stone, cost_growth, build_s,
#   build_growth, produces, rate/min, storage_bonus, max_level, req_lh, icon
BUILDINGS = [
    ("longhouse", "Longhouse", "progression", 2, 2, 50, 30, 1.7, 10, 1.8, "", 0, 0, 10, 1, "tile_0137"),
    ("lumber-camp", "Lumber Camp", "production", 1, 1, 20, 0, 1.6, 8, 1.7, "wood", 30, 0, 5, 1, "tile_0058"),
    ("farm", "Farm", "production", 1, 1, 25, 0, 1.6, 8, 1.7, "meat", 25, 0, 5, 1, "tile_0062"),
    ("quarry", "Quarry", "production", 1, 1, 30, 0, 1.6, 10, 1.7, "stone", 20, 0, 5, 2, "tile_0060"),
    ("storehouse", "Storehouse", "storage", 2, 2, 40, 20, 1.6, 12, 1.7, "", 0, 500, 5, 2, "tile_0085"),
]


def seed(apps, schema_editor):
    BuildingType = apps.get_model("game", "BuildingType")
    for (key, name, cat, fw, fh, cw, cs, cg, bs, bg,
         prod, rate, store, maxlvl, req, icon) in BUILDINGS:
        BuildingType.objects.update_or_create(
            key=key,
            defaults=dict(
                name=name, category=cat, footprint_w=fw, footprint_h=fh,
                cost_wood=cw, cost_stone=cs, cost_growth=cg,
                build_seconds=bs, build_growth=bg,
                produces=prod, production_rate=rate, storage_bonus=store,
                max_level=maxlvl, requires_longhouse_level=req, icon=icon,
            ),
        )


def unseed(apps, schema_editor):
    BuildingType = apps.get_model("game", "BuildingType")
    BuildingType.objects.filter(key__in=[b[0] for b in BUILDINGS]).delete()


class Migration(migrations.Migration):
    dependencies = [("game", "0008_buildingtype_village_building")]
    operations = [migrations.RunPython(seed, unseed)]
