"""Switch all icons to the Kenney Roguelike/RPG style (consistent look).

Environment sprites are named tile_XXXX, character/monster sprites char_XXXX.
Also renames "Healing Potion" -> "Healing Herb" to match its herb sprite (the
rogue packs have no potion bottle).
"""
from django.db import migrations

ITEM_ICONS = {
    "potion": "tile_0543",        # green herb with flower
    "iron-sword": "char_0422",    # steel sword
    "leather-armor": "char_0142", # brown shield
    "example-charm": "tile_0541", # herb (if the template plugin item exists)
}
MONSTER_ICONS = {
    "slime": "char_0162",     # green creature
    "goblin": "char_0163",    # green creature (red eyes)
    "orc": "char_0324",       # brawny brute
    "bandit": "char_0379",    # rough human
    "skeleton": "char_0271",  # pale figure
    "bat": "char_0432",       # humanoid stand-in (rogue pack has no animals)
    "wolf": "char_0487",      # humanoid stand-in
}


def apply_icons(apps, schema_editor):
    Item = apps.get_model("game", "Item")
    Monster = apps.get_model("game", "Monster")
    for key, icon in ITEM_ICONS.items():
        Item.objects.filter(key=key).update(icon=icon)
    for key, icon in MONSTER_ICONS.items():
        Monster.objects.filter(key=key).update(icon=icon)
    Item.objects.filter(key="potion").update(name="Healing Herb")


def revert(apps, schema_editor):
    apps.get_model("game", "Item").objects.filter(key="potion").update(name="Healing Potion")


class Migration(migrations.Migration):
    dependencies = [("game", "0005_item_icon_monster_icon")]
    operations = [migrations.RunPython(apply_icons, revert)]
