"""Django admin registrations.

Registering the models here gives a free management UI at /admin: a superuser can
create/edit items, tune monsters, adjust the balance config, and toggle plugins —
no extra code, no custom settings page.
"""
from django.contrib import admin

from .models import (
    Building, BuildingType, Character, GameConfig, InventoryItem, Item, MapArea,
    MapConnection, Monster, PluginState, Profile, Village,
)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "kind", "price", "heal",
                    "attack_bonus", "defense_bonus", "sellable", "icon")
    list_filter = ("kind", "sellable")
    search_fields = ("name", "key")


@admin.register(Monster)
class MonsterAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "max_hp", "attack", "defense",
                    "gold_reward", "xp_reward", "min_level", "sight_radius",
                    "biome", "icon")
    list_filter = ("biome",)
    search_fields = ("name", "key")


class MapConnectionInline(admin.TabularInline):
    model = MapConnection
    fk_name = "from_area"
    extra = 0


@admin.register(MapArea)
class MapAreaAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "biome", "size", "is_start")
    list_filter = ("biome", "is_start")
    search_fields = ("name", "key")
    inlines = [MapConnectionInline]


@admin.register(MapConnection)
class MapConnectionAdmin(admin.ModelAdmin):
    list_display = ("from_area", "kind", "to_area", "descend", "label")
    list_filter = ("kind", "descend")


class InventoryItemInline(admin.TabularInline):
    model = InventoryItem
    extra = 0


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "level", "xp", "hp", "max_hp", "gold")
    list_filter = ("level",)
    search_fields = ("name", "owner__username")
    inlines = [InventoryItemInline]


@admin.register(PluginState)
class PluginStateAdmin(admin.ModelAdmin):
    list_display = ("name", "enabled")
    list_editable = ("enabled",)  # flip plugins on/off right from the list


@admin.register(GameConfig)
class GameConfigAdmin(admin.ModelAdmin):
    list_display = ("__str__", "grid_size", "start_hp", "xp_base", "rest_cost")

    def has_add_permission(self, request):
        # Only ever one config row.
        return not GameConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BuildingType)
class BuildingTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "category", "cost_wood", "cost_stone",
                    "build_seconds", "produces", "production_rate",
                    "max_level", "requires_longhouse_level")
    list_filter = ("category", "produces")
    search_fields = ("name", "key")


class BuildingInline(admin.TabularInline):
    model = Building
    extra = 0


@admin.register(Village)
class VillageAdmin(admin.ModelAdmin):
    list_display = ("__str__", "wood", "stone", "meat", "last_tick")
    inlines = [BuildingInline]


admin.site.register(Profile)
