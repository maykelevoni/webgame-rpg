"""Data migration: seed the Mine — the Village building that produces iron.

Iron is the material the Castle Smithy spends to refine gear, so the Mine is the
production end of that chain. Requires Longhouse Lv 2 (so it's a small progression
goal), produces iron over time like the other production buildings. Admin-editable.
"""
from django.db import migrations

# key, name, emoji, category, fw, fh, cost_wood, cost_stone, build_s, produces,
#   rate/min, max_level, req_lh, max_counts
MINE = dict(
    key="mine", name="Mine", emoji="⛏️", category="production",
    footprint_w=1, footprint_h=1, cost_wood=35, cost_stone=20,
    build_seconds=12, produces="iron", production_rate=15,
    max_level=5, requires_longhouse_level=2, max_counts={"2": 1, "5": 2},
)


def seed(apps, schema_editor):
    BuildingType = apps.get_model("game", "BuildingType")
    BuildingType.objects.update_or_create(key=MINE["key"], defaults=MINE)


def unseed(apps, schema_editor):
    BuildingType = apps.get_model("game", "BuildingType")
    BuildingType.objects.filter(key=MINE["key"]).delete()


class Migration(migrations.Migration):
    dependencies = [("game", "0019_village_iron_alter_buildingtype_produces")]
    operations = [migrations.RunPython(seed, unseed)]
