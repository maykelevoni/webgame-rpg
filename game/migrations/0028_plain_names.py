"""Data migration: replace themed/Viking display names with plain, simple ones.
Keys are unchanged (internal IDs); only the human-facing ``name`` fields move.
"""
from django.db import migrations

BUILDINGS = {           # key -> new name
    "longhouse": "Town Hall",
    "quarry": "Quarry",          # was "Stonecutter"
    "hospital": "Tavern",        # was "Mead Hall"
}
AREAS = {
    "greenwood": "Forest",
    "old-mine": "Cave",
    "settlement": "Castle",
    "sunscorch-dunes": "Desert",
    "frostvale": "Snowfield",
}
MONSTERS = {
    "draug": "Wraith",
    "jotunn": "Giant",
}

OLD_BUILDINGS = {"longhouse": "Longhouse", "quarry": "Stonecutter", "hospital": "Mead Hall"}
OLD_AREAS = {"greenwood": "Greenwood", "old-mine": "Old Mine", "settlement": "Settlement",
             "sunscorch-dunes": "Sunscorch Dunes", "frostvale": "Frostvale"}
OLD_MONSTERS = {"draug": "Draug", "jotunn": "Jötunn"}


def _apply(apps, mapping, model_name):
    Model = apps.get_model("game", model_name)
    for key, name in mapping.items():
        Model.objects.filter(key=key).update(name=name)


def forwards(apps, schema_editor):
    _apply(apps, BUILDINGS, "BuildingType")
    _apply(apps, AREAS, "MapArea")
    _apply(apps, MONSTERS, "Monster")


def backwards(apps, schema_editor):
    _apply(apps, OLD_BUILDINGS, "BuildingType")
    _apply(apps, OLD_AREAS, "MapArea")
    _apply(apps, OLD_MONSTERS, "Monster")


class Migration(migrations.Migration):
    dependencies = [("game", "0027_seed_barracks")]
    operations = [migrations.RunPython(forwards, backwards)]
