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
    path("character/use-item/", views.use_item, name="use_item"),

    # world / movement
    path("play/", views.world_view, name="world"),
    path("play/move/", views.move, name="move"),

    # combat
    path("combat/", views.combat_view, name="combat"),
    path("combat/action/", views.combat_action, name="combat_action"),

    # town / shop
    path("town/", views.town_view, name="town"),
    path("town/action/", views.town_action, name="town_action"),
    path("town/rest/", views.rest, name="rest"),
    path("town/shop/", views.shop_view, name="shop"),
    path("town/shop/buy/", views.buy, name="buy"),
    path("town/shop/sell/", views.sell, name="sell"),
]
