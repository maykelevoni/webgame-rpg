"""Database models — the persistent side of the game, stored in Neon Postgres.

These hold *all* the game's data and balance numbers (characters, the item
catalog, monsters, plugin toggles, and the tuning config). Everything here is
editable in the Django admin, so the game can be rebalanced without code changes.

The pure-Python engine never imports this file. The bridge (`game/services.py`)
reads these rows and turns them into engine objects.
"""
from django.conf import settings
from django.db import models

# Item kinds — mirror the engine's constants.
ITEM_KINDS = [
    ("consumable", "Consumable"),
    ("weapon", "Weapon"),
    ("armor", "Armor"),
]


class Item(models.Model):
    """A thing the player can own/buy. The whole catalog lives in the DB."""
    key = models.SlugField(unique=True, help_text="Stable id, e.g. 'iron-sword'")
    name = models.CharField(max_length=80)
    kind = models.CharField(max_length=20, choices=ITEM_KINDS)
    price = models.PositiveIntegerField(default=0)
    heal = models.PositiveIntegerField(default=0, help_text="HP restored (consumables)")
    attack_bonus = models.PositiveIntegerField(default=0, help_text="When equipped (weapons)")
    defense_bonus = models.PositiveIntegerField(default=0, help_text="When equipped (armor)")
    sellable = models.BooleanField(default=True)
    icon = models.CharField(max_length=40, blank=True,
                            help_text="Sprite name in static/sprites, e.g. 'tile_0115'")

    def __str__(self):
        return self.name


class Monster(models.Model):
    """A base enemy. Tunable in admin; plugins may add more at runtime."""
    key = models.SlugField(unique=True)
    name = models.CharField(max_length=80)
    max_hp = models.PositiveIntegerField()
    attack = models.PositiveIntegerField()
    defense = models.PositiveIntegerField()
    gold_reward = models.PositiveIntegerField()
    xp_reward = models.PositiveIntegerField()
    min_level = models.PositiveIntegerField(default=1)
    icon = models.CharField(max_length=40, blank=True,
                            help_text="Sprite name in static/sprites, e.g. 'tile_0108'")

    def __str__(self):
        return self.name


class Character(models.Model):
    """A player's saved character. One per user for the MVP."""
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name="characters")
    name = models.CharField(max_length=40)

    level = models.PositiveIntegerField(default=1)
    xp = models.PositiveIntegerField(default=0)
    max_hp = models.PositiveIntegerField(default=30)
    hp = models.PositiveIntegerField(default=30)
    base_attack = models.PositiveIntegerField(default=8)
    base_defense = models.PositiveIntegerField(default=4)
    gold = models.PositiveIntegerField(default=0)

    # World state: the map is regenerated from this seed; `cleared` lists the
    # [x, y] tiles whose monster/treasure has already been dealt with.
    map_seed = models.BigIntegerField(default=0)
    pos_x = models.PositiveIntegerField(default=0)
    pos_y = models.PositiveIntegerField(default=0)
    cleared = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} (Lv {self.level})"


class InventoryItem(models.Model):
    """One stack of an item owned by a character."""
    character = models.ForeignKey(Character, on_delete=models.CASCADE,
                                  related_name="inventory")
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    equipped = models.BooleanField(default=False)
    slot = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"{self.quantity}x {self.item.name}"


class Profile(models.Model):
    """Per-user preferences that aren't part of a character (e.g. the theme)."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="profile")
    theme = models.CharField(max_length=50, default="dark-fantasy")

    def __str__(self):
        return f"Profile<{self.user}>"


class PluginState(models.Model):
    """Whether a plugin (a file in plugins/) is enabled. Toggled in admin."""
    name = models.CharField(max_length=100, unique=True)
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({'on' if self.enabled else 'off'})"


class GameConfig(models.Model):
    """A single row holding every balance knob. Edit it in the admin to tune the game."""
    start_hp = models.PositiveIntegerField(default=30)
    start_attack = models.PositiveIntegerField(default=8)
    start_defense = models.PositiveIntegerField(default=4)
    start_gold = models.PositiveIntegerField(default=20)

    grid_size = models.PositiveIntegerField(default=12)
    monster_count = models.PositiveIntegerField(default=14)
    treasure_count = models.PositiveIntegerField(default=6)

    xp_base = models.PositiveIntegerField(default=50)
    xp_growth = models.FloatField(default=1.5)
    stat_growth = models.PositiveIntegerField(default=3)

    rest_cost = models.PositiveIntegerField(default=10)
    treasure_gold_min = models.PositiveIntegerField(default=5)
    treasure_gold_max = models.PositiveIntegerField(default=25)

    class Meta:
        verbose_name = "Game config"
        verbose_name_plural = "Game config"

    def __str__(self):
        return "Game configuration"

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce a single row
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "GameConfig":
        """Return the one config row, creating it with defaults if missing."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
