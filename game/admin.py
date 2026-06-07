"""Django admin registrations.

Registering the models here gives a free management UI at /admin: a superuser can
create/edit items, tune monsters, adjust the balance config, and toggle plugins —
no extra code, no custom settings page.
"""
from django.contrib import admin

from .models import (
    Character, GameConfig, InventoryItem, Item, Monster, PluginState, Profile,
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
                    "gold_reward", "xp_reward", "min_level", "icon")
    search_fields = ("name", "key")


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


admin.site.register(Profile)
