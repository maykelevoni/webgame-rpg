"""Data migration: set per-Longhouse-level build limits on the seeded buildings.

This is the Clash-style cap — at Longhouse Lv 1 you may have just 1 Lumber Camp and
1 Farm; leveling the Longhouse unlocks more slots. All editable in the admin.
"""
from django.db import migrations

# key -> {longhouse_level: how many you may own from that level up}
LIMITS = {
    "lumber-camp": {"1": 1, "3": 2, "5": 3, "8": 4},
    "farm": {"1": 1, "3": 2, "5": 3, "8": 4},
    "quarry": {"2": 1, "4": 2, "7": 3},
    "storehouse": {"2": 1, "5": 2, "8": 3},
    # The Longhouse itself is founded with the village and never placed, but a
    # cap of 1 keeps it honest.
    "longhouse": {"1": 1},
}


def seed(apps, schema_editor):
    BuildingType = apps.get_model("game", "BuildingType")
    for key, counts in LIMITS.items():
        BuildingType.objects.filter(key=key).update(max_counts=counts)


def unseed(apps, schema_editor):
    BuildingType = apps.get_model("game", "BuildingType")
    BuildingType.objects.filter(key__in=LIMITS).update(max_counts={})


class Migration(migrations.Migration):
    dependencies = [("game", "0010_buildingtype_max_counts")]
    operations = [migrations.RunPython(seed, unseed)]
