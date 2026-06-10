"""Data migration: place the areas on the strategic World Map (0-100 grid).

The Castle (settlement) sits at the centre; biomes radiate out at increasing
distance, so farther = longer travel = tougher/richer. The Cave shares the Forest's
spot (you descend into it from the surface). Idempotent.
"""
from django.db import migrations

# key -> (world_x, world_y). Centre is (50, 50).
COORDS = {
    "settlement": (50, 50),       # Castle — the hub you set out from
    "greenwood": (38, 42),        # Forest — close starter zone
    "old-mine": (34, 60),         # Cave — near the forest
    "sunscorch-dunes": (74, 64),  # Desert — farther out
    "frostvale": (22, 20),        # Snowfield — far, cold corner
}


def seed(apps, schema_editor):
    MapArea = apps.get_model("game", "MapArea")
    for key, (x, y) in COORDS.items():
        MapArea.objects.filter(key=key).update(world_x=x, world_y=y)


def unseed(apps, schema_editor):
    MapArea = apps.get_model("game", "MapArea")
    MapArea.objects.all().update(world_x=50, world_y=50)


class Migration(migrations.Migration):
    dependencies = [("game", "0029_character_travel_arrive_at_character_travel_dest_key_and_more")]
    operations = [migrations.RunPython(seed, unseed)]
