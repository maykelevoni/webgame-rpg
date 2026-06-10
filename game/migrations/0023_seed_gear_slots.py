"""Data migration: give gear equipment slots + seed one starter item per slot.

Moves the catalog onto the MU-style slot system (weapon/shield/helmet/armor/boots/
amulet). Existing gear gets its slot; new basic pieces fill the rest so the shop has
something for every slot. All are refinable at the Smithy. Admin-editable after.
"""
from django.db import migrations

# key, name, kind, slot, price, atk, def, icon
GEAR = [
    ("iron-sword",    "Iron Sword",    "weapon", "weapon", 40, 5, 0, "char_0422"),
    ("wooden-shield", "Wooden Shield", "armor",  "shield", 30, 0, 2, ""),
    ("iron-helm",     "Iron Helm",     "armor",  "helmet", 30, 0, 2, ""),
    ("leather-armor", "Leather Armor", "armor",  "armor",  35, 0, 3, ""),
    ("leather-boots", "Leather Boots", "armor",  "boots",  20, 0, 1, ""),
    ("bone-amulet",   "Bone Amulet",   "armor",  "amulet", 45, 1, 1, ""),
]


def seed(apps, schema_editor):
    Item = apps.get_model("game", "Item")
    for key, name, kind, slot, price, atk, df, icon in GEAR:
        Item.objects.update_or_create(
            key=key,
            defaults=dict(name=name, kind=kind, slot=slot, price=price,
                          attack_bonus=atk, defense_bonus=df, icon=icon,
                          heal=0, sellable=True),
        )


def unseed(apps, schema_editor):
    Item = apps.get_model("game", "Item")
    # Drop the newly-added pieces; clear slots on the pre-existing ones.
    Item.objects.filter(key__in=["wooden-shield", "iron-helm",
                                 "leather-boots", "bone-amulet"]).delete()
    Item.objects.filter(key__in=["iron-sword", "leather-armor"]).update(slot="")


class Migration(migrations.Migration):
    dependencies = [("game", "0022_item_slot")]
    operations = [migrations.RunPython(seed, unseed)]
