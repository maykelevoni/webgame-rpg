"""Views — the thin Django layer.

Each view does as little as possible: read the request, call a `services` function
(which runs the engine and touches the DB), then render a template or redirect.
There are no game rules here — those live in the engine.
"""
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from engine.leveling import xp_to_next

from . import services
from .identity import get_current_player
from .models import Item, Profile


# ----- public / auth ------------------------------------------------------
def home(request):
    character = get_current_player(request) if request.user.is_authenticated else None
    return render(request, "home.html", {"character": character})


def signup(request):
    """Register a new player and log them straight in."""
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("game:character_create")
    else:
        form = UserCreationForm()
    return render(request, "registration/signup.html", {"form": form})


@require_POST
@login_required
def set_theme(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    profile.theme = request.POST.get("theme", profile.theme)
    profile.save()
    return redirect(request.POST.get("next") or "game:home")


# ----- character ----------------------------------------------------------
@login_required
def character_create(request):
    if get_current_player(request):
        return redirect("game:world")
    if request.method == "POST":
        name = request.POST.get("name", "").strip() or "Hero"
        services.create_character(request.user, name)
        return redirect("game:world")
    return render(request, "character_create.html")


@login_required
def character_sheet(request):
    char = get_current_player(request)
    if not char:
        return redirect("game:character_create")
    catalog = services.load_catalog()
    engine_char = services.character_to_engine(char, catalog)
    cfg = services.load_config()
    ctx = {
        "char": char,
        "eff_atk": engine_char.effective_attack(),
        "eff_def": engine_char.effective_defense(),
        "next_xp": xp_to_next(char.level, cfg.xp_base, cfg.xp_growth),
        "inventory": engine_char.inventory,
    }
    return render(request, "character_sheet.html", ctx)


@require_POST
@login_required
def equip(request):
    messages.info(request, services.equip_item(request.user, request.POST.get("item_key", "")))
    return redirect(request.POST.get("next") or "game:character_sheet")


@require_POST
@login_required
def use_item(request):
    messages.info(request, services.use_item(request.user, request.POST.get("item_key", "")))
    return redirect(request.POST.get("next") or "game:character_sheet")


# ----- world / movement ---------------------------------------------------
@login_required
def world_view(request):
    char = get_current_player(request)
    if not char:
        return redirect("game:character_create")
    if request.session.get("combat"):
        return redirect("game:combat")
    grid, size = services.build_grid(char, services.load_config())
    return render(request, "world.html", {
        "char": char, "grid": grid, "size": size,
        "floor_sprite": services.FLOOR_SPRITE,
    })


@require_POST
@login_required
def move(request):
    if request.session.get("combat"):
        return redirect("game:combat")
    result = services.do_move(request, request.POST.get("direction", ""))
    kind = result["kind"]
    if kind == "monster":
        return redirect("game:combat")
    if kind == "town":
        return redirect("game:town")
    if kind == "treasure":
        messages.success(request, f"You found {result['gold']} gold!")
    return redirect("game:world")


# ----- combat -------------------------------------------------------------
@login_required
def combat_view(request):
    fight, char = services.get_combat(request)
    if not fight:
        return redirect("game:world")
    potions = [e for e in fight.character.inventory
               if e.item.kind == "consumable" and e.quantity > 0]
    return render(request, "combat.html",
                  {"fight": fight, "char": char, "potions": potions})


@require_POST
@login_required
def combat_action(request):
    fight = services.combat_action(
        request, request.POST.get("action", ""), request.POST.get("item_key"))
    if fight is None:
        return redirect("game:world")
    if not fight.is_over:
        return redirect("game:combat")
    if fight.outcome == "win":
        gold, xp = fight.rewards()
        messages.success(request, f"Victory! +{gold} gold, +{xp} XP.")
        if getattr(fight, "area_cleared", False):
            messages.success(request, "You cleared the whole area — a new region unfolds!")
        return redirect("game:world")
    if fight.outcome == "lose":
        messages.error(request, "You were defeated and woke up in town (lost half your gold).")
        return redirect("game:town")
    messages.info(request, "You fled the battle.")
    return redirect("game:world")


# ----- town / shop --------------------------------------------------------
@login_required
def town_view(request):
    char = get_current_player(request)
    if not char:
        return redirect("game:character_create")
    registry = services.get_active_plugins()
    return render(request, "town.html",
                  {"char": char, "plugin_actions": list(registry.town_actions.keys())})


@require_POST
@login_required
def town_action(request):
    """Run a plugin-provided town action (e.g. the example 'Pray at Shrine')."""
    label = request.POST.get("label", "")
    registry = services.get_active_plugins()
    handler = registry.town_actions.get(label)
    if handler:
        model = get_current_player(request)
        engine_char = services.character_to_engine(model, services.load_catalog())
        result_message = handler(engine_char)
        services.save_engine_character(engine_char, model)
        messages.info(request, result_message or f"{label}.")
    return redirect("game:town")


@require_POST
@login_required
def rest(request):
    messages.info(request, services.rest(request.user))
    return redirect("game:town")


@require_POST
@login_required
def leave_town(request):
    services.leave_town(request.user)
    return redirect("game:world")


@login_required
def shop_view(request):
    char = get_current_player(request)
    if not char:
        return redirect("game:character_create")
    return render(request, "shop.html", {
        "char": char,
        "items": Item.objects.all(),
        "inventory": char.inventory.select_related("item").all(),
    })


@require_POST
@login_required
def buy(request):
    messages.info(request, services.buy_item(request.user, request.POST.get("item_key", "")))
    return redirect("game:shop")


@require_POST
@login_required
def sell(request):
    messages.info(request, services.sell_item(request.user, request.POST.get("item_key", "")))
    return redirect("game:shop")
