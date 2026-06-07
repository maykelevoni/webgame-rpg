"""Register the example plugin's enable/disable toggle (enabled by default).

The app also auto-creates a PluginState row for any plugin file it discovers, but
seeding it here means the toggle is present in the admin right away.
"""
from django.db import migrations


def seed(apps, schema_editor):
    PluginState = apps.get_model("game", "PluginState")
    PluginState.objects.get_or_create(name="healing_shrine", defaults={"enabled": True})


def unseed(apps, schema_editor):
    PluginState = apps.get_model("game", "PluginState")
    PluginState.objects.filter(name="healing_shrine").delete()


class Migration(migrations.Migration):
    dependencies = [("game", "0002_seed_data")]
    operations = [migrations.RunPython(seed, unseed)]
