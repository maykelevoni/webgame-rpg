"""Data migration: split the Castle from the Village.

The Castle (the `city` MapArea you enter from the world map) is now a **fixed authored
hub** of NPC service stations (defined in `services.CASTLE_STATIONS`), the same for every
player — it is no longer rendered from the player's own buildings. So the Market and
Mead Hall (key `hospital`) that Phase 2a auto-placed *inside each Village* don't belong
there anymore: remove those building instances. The Village now holds only production
buildings + the Longhouse.

Reversible-ish: the down migration is a no-op (we don't re-place the services, since the
service auto-placement code is gone — the castle owns them now).
"""
from django.db import migrations

SERVICE_KEYS = ("market", "hospital")


def split(apps, schema_editor):
    Building = apps.get_model("game", "Building")
    Building.objects.filter(type__key__in=SERVICE_KEYS).delete()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("game", "0017_emoji_and_beasts")]
    operations = [migrations.RunPython(split, noop)]
