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

# Equipment slots (MU-style paper-doll). A piece of gear declares one slot; only one
# item per slot can be worn at a time. Consumables have no slot.
EQUIP_SLOTS = [
    ("weapon", "Weapon"),
    ("shield", "Shield"),
    ("helmet", "Helmet"),
    ("armor", "Armor"),
    ("boots", "Boots"),
    ("amulet", "Amulet"),
]


class Item(models.Model):
    """A thing the player can own/buy. The whole catalog lives in the DB."""
    key = models.SlugField(unique=True, help_text="Stable id, e.g. 'iron-sword'")
    name = models.CharField(max_length=80)
    kind = models.CharField(max_length=20, choices=ITEM_KINDS)
    slot = models.CharField(max_length=20, choices=EQUIP_SLOTS, blank=True,
                            help_text="Equipment slot (gear only; blank for consumables)")
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
    sight_radius = models.PositiveIntegerField(
        default=4, help_text="How far (tiles) it spots and chases the player")
    biome = models.CharField(
        max_length=20, blank=True,
        help_text="Restrict spawns to this biome (blank = any)")
    icon = models.CharField(max_length=40, blank=True,
                            help_text="Sprite name in static/sprites, e.g. 'tile_0108'")
    emoji = models.CharField(max_length=8, blank=True,
                             help_text="Emoji shown on the map/combat, e.g. '🐺' (preferred over icon)")

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
    # Gold stashed at the Castle Vault — safe from the death penalty (which only
    # halves *carried* gold). Deposit/withdraw at the 💰 station.
    vault_gold = models.PositiveIntegerField(default=0)

    # World state. `pos_x`/`pos_y` are the position *within the current area*.
    # `area_state` holds per-area exploration state, keyed by area key:
    #   {"greenwood": {"cleared": [[x,y],...], "monsters": [{...}], "seed": n}}
    # `map_seed`/`cleared` are legacy from the single-world era (kept for migration).
    current_area = models.ForeignKey("MapArea", null=True, blank=True,
                                     on_delete=models.SET_NULL,
                                     related_name="characters_here")
    area_state = models.JSONField(default=dict, blank=True)
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
    refine_level = models.PositiveIntegerField(default=0, help_text="Smithy +level")

    def __str__(self):
        plus = f" +{self.refine_level}" if self.refine_level else ""
        return f"{self.quantity}x {self.item.name}{plus}"


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


# --------------------------------------------------------------------------
# Village / empire — the second progression loop (see docs/village-design.md).
# --------------------------------------------------------------------------
BUILDING_CATEGORIES = [
    ("production", "Production"),
    ("storage", "Storage"),
    ("progression", "Progression"),
    ("service", "Service"),
    ("military", "Military"),
    ("defense", "Defense"),
]

# Resources a building can produce (mirrors engine.village.RESOURCES).
RESOURCE_CHOICES = [("", "None"), ("wood", "Wood"), ("stone", "Stone"),
                    ("meat", "Meat"), ("iron", "Iron")]


class BuildingType(models.Model):
    """The catalog of buildable things. All costs/times/rates are admin-tunable —
    the engine just reads whatever these rows say (loaded via services)."""
    key = models.SlugField(unique=True, help_text="Stable id, e.g. 'lumber-camp'")
    name = models.CharField(max_length=80)
    category = models.CharField(max_length=20, choices=BUILDING_CATEGORIES,
                                default="production")
    footprint_w = models.PositiveIntegerField(default=1)
    footprint_h = models.PositiveIntegerField(default=1)

    cost_wood = models.PositiveIntegerField(default=0)
    cost_stone = models.PositiveIntegerField(default=0)
    cost_growth = models.FloatField(default=1.6, help_text="Cost multiplier per level")

    build_seconds = models.PositiveIntegerField(default=5, help_text="Build time at level 1")
    build_growth = models.FloatField(default=1.7, help_text="Build-time multiplier per level")

    produces = models.CharField(max_length=10, choices=RESOURCE_CHOICES, blank=True, default="")
    production_rate = models.PositiveIntegerField(default=0, help_text="Units/min at level 1")
    storage_bonus = models.PositiveIntegerField(default=0, help_text="Added to resource cap, per level")

    max_level = models.PositiveIntegerField(default=5)
    requires_longhouse_level = models.PositiveIntegerField(default=1)
    max_counts = models.JSONField(
        default=dict, blank=True,
        help_text='How many you may own, by Longhouse level. '
                  'e.g. {"1": 1, "3": 2, "5": 3} = 1 at LH1, 2 at LH3, 3 at LH5.')
    icon = models.CharField(max_length=40, blank=True,
                            help_text="Sprite name in static/sprites, e.g. 'tile_0058'")
    emoji = models.CharField(max_length=8, blank=True,
                             help_text="Emoji shown on the map/grid, e.g. '🔨' (preferred over icon)")

    def __str__(self):
        return self.name


class Village(models.Model):
    """A character's base. One per character. Resources + the last time we ran the
    production/build 'tick' (so we can catch up on offline time)."""
    character = models.OneToOneField(Character, on_delete=models.CASCADE,
                                     related_name="village")
    wood = models.PositiveIntegerField(default=0)
    stone = models.PositiveIntegerField(default=0)
    meat = models.PositiveIntegerField(default=0)
    iron = models.PositiveIntegerField(default=0)
    last_tick = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Village of {self.character.name}"


class Building(models.Model):
    """One placed building. ``level`` is the completed level; while
    ``build_finish_at`` is set it's working toward the next level."""
    village = models.ForeignKey(Village, on_delete=models.CASCADE, related_name="buildings")
    type = models.ForeignKey(BuildingType, on_delete=models.CASCADE)
    level = models.PositiveIntegerField(default=0)
    pos_x = models.PositiveIntegerField(default=0)
    pos_y = models.PositiveIntegerField(default=0)
    build_finish_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.type.name} Lv{self.level} @({self.pos_x},{self.pos_y})"


# --------------------------------------------------------------------------
# Maps / exploration — the connected world (see docs/maps-exploration-design.md).
# --------------------------------------------------------------------------
BIOME_CHOICES = [
    ("grass", "Grass / Forest"),
    ("desert", "Desert / Sand"),
    ("ice", "Ice"),
    ("dungeon", "Dungeon / Mine"),
    ("city", "City"),
]


class MapArea(models.Model):
    """One explorable place. Its layout is generated procedurally from `seed` +
    `biome`; remembered surface areas keep a stable seed, dungeons get a fresh one
    each descent. The world graph (which area connects to which) is the set of
    MapConnection rows."""
    key = models.SlugField(unique=True, help_text="Stable id, e.g. 'greenwood'")
    name = models.CharField(max_length=80)
    biome = models.CharField(max_length=20, choices=BIOME_CHOICES, default="grass")
    seed = models.BigIntegerField(default=1, help_text="Layout seed for surface areas")
    size = models.PositiveIntegerField(default=12)
    is_start = models.BooleanField(default=False, help_text="Where new characters begin")

    def __str__(self):
        return self.name


CONNECTION_KINDS = [
    ("door", "Door"),
    ("mine", "Mine entrance"),
    ("hole", "Hole with stairs"),
    ("stairs", "Stairs"),
    ("portal", "Portal"),
    ("town", "To town (menu)"),
]


class MapConnection(models.Model):
    """A one-way link out of an area. ``to_area`` is the destination; when ``kind``
    is 'town' (and ``to_area`` is blank) it routes to the existing town menu. A
    'hole'/'stairs' into a dungeon descends to a freshly generated level."""
    from_area = models.ForeignKey(MapArea, on_delete=models.CASCADE,
                                  related_name="exits")
    to_area = models.ForeignKey(MapArea, null=True, blank=True,
                                on_delete=models.CASCADE, related_name="entrances")
    kind = models.CharField(max_length=20, choices=CONNECTION_KINDS, default="door")
    label = models.CharField(max_length=40, blank=True)
    descend = models.BooleanField(
        default=False, help_text="Generate a fresh level on use (dungeon depth)")

    def __str__(self):
        dest = self.to_area.name if self.to_area else self.get_kind_display()
        return f"{self.from_area.key} → {dest} ({self.kind})"


class GameConfig(models.Model):
    """A single row holding every balance knob. Edit it in the admin to tune the game."""
    start_hp = models.PositiveIntegerField(default=30)
    start_attack = models.PositiveIntegerField(default=8)
    start_defense = models.PositiveIntegerField(default=4)
    start_gold = models.PositiveIntegerField(default=20)

    grid_size = models.PositiveIntegerField(default=12)
    monster_count = models.PositiveIntegerField(default=14)  # legacy; monsters are now hidden
    treasure_count = models.PositiveIntegerField(default=5)
    encounter_rate = models.FloatField(
        default=0.18, help_text="Chance (0-1) of a random battle per step on grass")

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
