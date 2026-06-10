"""Game URL routes."""
from django.urls import path

from . import views

app_name = "game"

urlpatterns = [
    path("", views.home, name="home"),
    path("settings/theme/", views.set_theme, name="set_theme"),

    # character
    path("character/create/", views.character_create, name="character_create"),
    path("character/", views.character_sheet, name="character_sheet"),
    path("character/equip/", views.equip, name="equip"),
    path("character/unequip/", views.unequip, name="unequip"),
    path("character/use-item/", views.use_item, name="use_item"),
    path("character/inventory/data/", views.inventory_data, name="inventory_data"),

    # world / movement
    path("play/", views.world_view, name="world"),
    path("play/move/", views.move, name="move"),
    path("play/harvest/", views.harvest, name="harvest"),
    path("play/open-chest/", views.open_chest, name="open_chest"),

    # combat
    path("combat/", views.combat_view, name="combat"),
    path("combat/action/", views.combat_action, name="combat_action"),

    # village / empire
    path("village/", views.village_view, name="village"),
    path("village/place/", views.village_place, name="village_place"),
    path("village/upgrade/", views.village_upgrade, name="village_upgrade"),

    # town / shop
    path("town/", views.town_view, name="town"),
    path("town/action/", views.town_action, name="town_action"),
    path("town/rest/", views.rest, name="rest"),
    path("town/leave/", views.leave_town, name="leave_town"),
    path("town/shop/", views.shop_view, name="shop"),
    path("town/shop/data/", views.shop_data, name="shop_data"),
    path("town/shop/buy/", views.buy, name="buy"),
    path("town/shop/sell/", views.sell, name="sell"),
    path("town/shop/sell-resource/", views.sell_resource, name="sell_resource"),

    # castle smithy (refine gear)
    path("castle/smithy/", views.smithy_data, name="smithy_data"),
    path("castle/smithy/refine/", views.refine, name="refine"),

    # castle vault (stash gold)
    path("castle/vault/", views.vault_data, name="vault_data"),
    path("castle/vault/move/", views.vault_move, name="vault_move"),
]
