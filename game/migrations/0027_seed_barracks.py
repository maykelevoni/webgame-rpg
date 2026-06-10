"""Data migration: seed the Barracks — the Village building that lets you train a
warband for raids (army/raiding slice 2).

It produces nothing on its own; its presence (built, Lv >= 1) unlocks troop
training, and its level raises how many warriors you may train at once (see
services.train_troops). Requires Longhouse Lv 3 — a mid-game military goal.
Admin-editable like every other building.
"""
from django.db import migrations

BARRACKS = dict(
    key="barracks", name="Barracks", emoji="⚔️", category="military",
    footprint_w=2, footprint_h=2, cost_wood=80, cost_stone=60,
    build_seconds=30, produces="", production_rate=0,
    max_level=5, requires_longhouse_level=3, max_counts={"3": 1, "8": 2},
)


def seed(apps, schema_editor):
    BuildingType = apps.get_model("game", "BuildingType")
    BuildingType.objects.update_or_create(key=BARRACKS["key"], defaults=BARRACKS)


def unseed(apps, schema_editor):
    BuildingType = apps.get_model("game", "BuildingType")
    BuildingType.objects.filter(key=BARRACKS["key"]).delete()


class Migration(migrations.Migration):
    dependencies = [("game", "0026_character_recovering_until_village_troops_and_more")]
    operations = [migrations.RunPython(seed, unseed)]
