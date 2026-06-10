"""Data migration: the walkable settlement (Village Phase 2a).

Adds the pre-built **Market** and **Hospital** service buildings, creates the single
shared **settlement** MapArea (biome 'city') whose layout is rendered per-character
from that character's buildings, and rewires the world so the 🏠 connection *enters*
the settlement instead of opening the legacy town menu:

    Greenwood --🏠 (town)--> Settlement   (was: to the /town/ menu)
    Settlement --door--> Greenwood        (the gate out)

The Market/Hospital buildings themselves are pre-placed lazily by
``services.get_or_create_village`` (one code path for both new and existing
villages), so this migration only seeds the catalog and the world graph.
Idempotent and reversible.
"""
from django.db import migrations

# key, name, footprint w/h, icon — services produce nothing and aren't player-built.
SERVICES = [
    ("market", "Market", 1, 1, "tile_0085"),
    ("hospital", "Hospital", 1, 1, "tile_0084"),
]


def seed(apps, schema_editor):
    BuildingType = apps.get_model("game", "BuildingType")
    MapArea = apps.get_model("game", "MapArea")
    MapConnection = apps.get_model("game", "MapConnection")

    for key, name, fw, fh, icon in SERVICES:
        BuildingType.objects.update_or_create(
            key=key,
            defaults=dict(
                name=name, category="service", footprint_w=fw, footprint_h=fh,
                cost_wood=0, cost_stone=0, produces="", production_rate=0,
                storage_bonus=0, max_level=1, requires_longhouse_level=1,
                max_counts={"1": 1}, icon=icon,
            ),
        )

    settlement, _ = MapArea.objects.update_or_create(
        key="settlement",
        defaults=dict(name="Settlement", biome="city", seed=1, size=6,
                      is_start=False))

    greenwood = MapArea.objects.filter(key="greenwood").first()
    if greenwood:
        # Repoint the 🏠 connection (kept kind 'town' for its icon) at the settlement.
        town = MapConnection.objects.filter(
            from_area=greenwood, kind="town").first()
        if town:
            town.to_area = settlement
            town.label = town.label or "Settlement"
            town.save()
        else:
            MapConnection.objects.create(
                from_area=greenwood, to_area=settlement, kind="town",
                label="Settlement")
        # The gate out of the settlement, back to the surface.
        MapConnection.objects.get_or_create(
            from_area=settlement, to_area=greenwood, kind="door",
            defaults=dict(label="Leave"))


def unseed(apps, schema_editor):
    BuildingType = apps.get_model("game", "BuildingType")
    Building = apps.get_model("game", "Building")
    MapArea = apps.get_model("game", "MapArea")
    MapConnection = apps.get_model("game", "MapConnection")

    greenwood = MapArea.objects.filter(key="greenwood").first()
    if greenwood:
        MapConnection.objects.filter(
            from_area=greenwood, kind="town").update(to_area=None, label="Town")
    MapConnection.objects.filter(from_area__key="settlement").delete()
    MapArea.objects.filter(key="settlement").delete()
    Building.objects.filter(type__key__in=[s[0] for s in SERVICES]).delete()
    BuildingType.objects.filter(key__in=[s[0] for s in SERVICES]).delete()


class Migration(migrations.Migration):
    dependencies = [("game", "0014_alter_buildingtype_category")]
    operations = [migrations.RunPython(seed, unseed)]
