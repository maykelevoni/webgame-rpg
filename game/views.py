"""Views — the thin Django layer.

Each view does as little as possible: read the request, call a `services` function
(which runs the engine and touches the DB), then render a template or redirect.
There are no game rules here — those live in the engine.
"""
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from engine.leveling import xp_to_next

from . import services
from .identity import get_current_player
from .models import Item, Profile


def _is_ajax(request) -> bool:
    """True when the request came from explore.js (fetch), not a plain form post."""
    return request.headers.get("x-requested-with") == "fetch"


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
    cfg = services.load_config()
    payload = services.inventory_payload(request.user)
    ctx = {
        "char": char,
        "eff_atk": payload["eff_atk"],
        "eff_def": payload["eff_def"],
        "next_xp": xp_to_next(char.level, cfg.xp_base, cfg.xp_growth),
        "slots": payload["slots"],
        "pack": [i for i in payload["inventory"] if not i["equipped"]],
    }
    return render(request, "character_sheet.html", ctx)


@require_POST
@login_required
def equip(request):
    msg = services.equip_item(request.user, request.POST.get("item_key", ""))
    if _is_ajax(request):
        return JsonResponse({"message": msg, **services.inventory_payload(request.user)})
    messages.info(request, msg)
    return redirect(request.POST.get("next") or "game:character_sheet")


@require_POST
@login_required
def unequip(request):
    msg = services.unequip_item(request.user, request.POST.get("slot", ""))
    if _is_ajax(request):
        return JsonResponse({"message": msg, **services.inventory_payload(request.user)})
    messages.info(request, msg)
    return redirect(request.POST.get("next") or "game:character_sheet")


@require_POST
@login_required
def use_item(request):
    msg = services.use_item(request.user, request.POST.get("item_key", ""))
    if _is_ajax(request):
        return JsonResponse({"message": msg, **services.inventory_payload(request.user)})
    messages.info(request, msg)
    return redirect(request.POST.get("next") or "game:character_sheet")


@login_required
def inventory_data(request):
    """Paper-doll + inventory + stats for the on-map inventory modal."""
    return JsonResponse(services.inventory_payload(request.user))


# ----- world / movement ---------------------------------------------------
@login_required
def world_view(request):
    char = get_current_player(request)
    if not char:
        return redirect("game:character_create")
    cfg = services.load_config()
    area = services.get_area(char)
    ctx = {
        "char": char, "area": area,
        "floor_sprite": services.FLOOR_SPRITE,
        "next_xp": xp_to_next(char.level, cfg.xp_base, cfg.xp_growth),
        "recovery": services.hero_recovery(char),
    }
    if area is None:
        ctx["no_area"] = True
    else:
        grid, size = services.build_map_grid(char, area)
        ctx.update({"grid": grid, "size": size})
    # If a battle is in progress, hand the template the fight so it can show the
    # Pokémon-style overlay on top of the map.
    fight, _ = services.get_combat(request)
    if fight:
        ctx["fight"] = fight
        ctx["potions"] = [e for e in fight.character.inventory
                          if e.item.kind == "consumable" and e.quantity > 0]
    # A just-finished fight shows its result as a modal (popped so it shows once).
    if "combat_result" in request.session:
        ctx["combat_result"] = request.session.pop("combat_result")
    return render(request, "world.html", ctx)


@require_POST
@login_required
def move(request):
    ajax = _is_ajax(request)
    if request.session.get("combat"):     # mid-battle: ignore movement
        return JsonResponse({"combat": True}) if ajax else redirect("game:world")

    rec = services.hero_recovery(get_current_player(request))
    if rec["recovering"]:                 # downed in a raid: can't explore yet
        msg = f"You're still recovering from your last raid ({rec['seconds_left']}s left)."
        if ajax:
            return JsonResponse({"recovering": True, "message": msg,
                                 "seconds_left": rec["seconds_left"]})
        messages.info(request, msg)
        return redirect("game:world")

    result = services.do_move(request, request.POST.get("direction", ""))
    kind = result["kind"]

    if not ajax:
        # No-JS fallback: harvest instantly (no mini-game), message + redirect.
        if kind == "building":
            key = result["building"]
            if key == "market":
                return redirect("game:shop")
            if key == "hospital":
                messages.info(request, services.rest(request.user))
                return redirect("game:world")
            return redirect("game:village")        # longhouse / build UI
        if kind == "resource":
            r = services.harvest_node(get_current_player(request), 1.0)
            if r:
                messages.success(request, f"You gather {r['amount']} {r['resource']}.")
        elif kind == "chest":
            r = services.open_chest_node(get_current_player(request))
            if r:
                messages.success(request, f"You open a chest — +{r['gold']} gold!")
        elif kind == "encounter":
            messages.warning(request, "A monster catches you — defend yourself!")
        return redirect("game:world")

    # explore.js: paint the result in place — no full reload.
    if kind == "encounter":
        return JsonResponse({"combat": True})
    if kind == "building":
        return JsonResponse({"building": result["building"]})

    char = get_current_player(request)
    area = services.get_area(char)
    grid, size = services.build_map_grid(char, area)
    payload = {
        "grid": grid, "size": size, "area": area.name if area else "",
        "biome": area.biome if area else "",
        "hp": char.hp, "max_hp": char.max_hp, "gold": char.gold,
    }
    # Stepping onto a node tells the client which mini-game to open.
    if kind == "resource":
        payload["minigame"] = "resource"
        payload["resource"] = result["resource"]
    elif kind == "chest":
        payload["minigame"] = "chest"
    return JsonResponse(payload)


@require_POST
@login_required
def harvest(request):
    """Collect the resource node under the player; quality (0..1) from the mini-game."""
    char = get_current_player(request)
    try:
        quality = float(request.POST.get("quality", "0"))
    except ValueError:
        quality = 0.0
    result = services.harvest_node(char, quality)
    if result is None:
        return JsonResponse({"error": "Nothing to harvest here."}, status=400)
    area = services.get_area(char)
    grid, size = services.build_map_grid(char, area)
    return JsonResponse({**result, "grid": grid, "size": size, "gold": char.gold})


@require_POST
@login_required
def open_chest(request):
    char = get_current_player(request)
    try:
        quality = float(request.POST.get("quality", "1"))
    except ValueError:
        quality = 1.0
    result = services.open_chest_node(char, quality)
    if result is None:
        return JsonResponse({"error": "No chest here."}, status=400)
    area = services.get_area(char)
    grid, size = services.build_map_grid(char, area)
    # `gold_gain` is what the chest gave; `gold` is the new running total (for the HUD).
    return JsonResponse({"gold_gain": result["gold"], "grid": grid, "size": size,
                         "gold": char.gold})


# ----- combat (rendered as an overlay on the world page) ------------------
@login_required
def combat_view(request):
    # Combat now lives as an overlay on /play/; send any direct hits there.
    return redirect("game:world")


@require_POST
@login_required
def combat_action(request):
    ajax = _is_ajax(request)
    fight = services.combat_action(
        request, request.POST.get("action", ""), request.POST.get("item_key"))
    if fight is None:
        return JsonResponse({"error": "no fight"}, status=400) if ajax else redirect("game:world")

    if ajax:
        # explore.js drives combat in place: bars/log update, monster shakes on hit.
        payload = {
            "outcome": fight.outcome,        # ongoing / win / lose / fled
            "monster": fight.monster.name,
            "monster_hp": fight.monster_hp, "monster_max": fight.monster.max_hp,
            "player_hp": fight.character.hp, "player_max": fight.character.max_hp,
            "log": fight.log,
        }
        if fight.outcome == "win":
            payload["gold"], payload["xp"] = fight.rewards()
        return JsonResponse(payload)

    if fight.is_over:
        # Hand the outcome to the map as a modal (no message banner).
        if fight.outcome == "win":
            gold, xp = fight.rewards()
            request.session["combat_result"] = {
                "outcome": "win", "gold": gold, "xp": xp, "monster": fight.monster.name}
        elif fight.outcome == "lose":
            request.session["combat_result"] = {"outcome": "lose"}
        else:
            request.session["combat_result"] = {"outcome": "fled"}
    return redirect("game:world")


# ----- shop / castle services ---------------------------------------------
@require_POST
@login_required
def rest(request):
    msg = services.rest(request.user)
    if _is_ajax(request):
        return JsonResponse({"message": msg, **services.shop_payload(request.user)})
    messages.info(request, msg)
    return redirect("game:world")


@login_required
def shop_data(request):
    """Items + inventory + gold for the on-map market modal."""
    return JsonResponse(services.shop_payload(request.user))


@login_required
def smithy_data(request):
    """The player's refinable gear + iron/gold for the Castle Smithy panel."""
    return JsonResponse(services.smithy_payload(request.user))


@require_POST
@login_required
def refine(request):
    """Attempt one refine (+1) at the Smithy; returns the result + fresh panel."""
    result = services.refine_item(request.user, _int(request.POST.get("inv_id"), 0))
    status = 400 if "error" in result else 200
    return JsonResponse(result, status=status)


@login_required
def vault_data(request):
    """Carried + stashed gold for the Castle Vault panel."""
    return JsonResponse(services.vault_payload(request.user))


@require_POST
@login_required
def vault_move(request):
    """Deposit/withdraw gold at the Vault; returns the updated balances."""
    result = services.vault_action(
        request.user, request.POST.get("action", ""), request.POST.get("amount"))
    status = 400 if "error" in result else 200
    return JsonResponse(result, status=status)


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


# ----- village / empire ---------------------------------------------------
@login_required
def village_view(request):
    char = get_current_player(request)
    if not char:
        return redirect("game:character_create")
    overview = services.village_overview(char)
    for event in overview.pop("events"):
        messages.info(request, event)
    return render(request, "village.html",
                  {"char": char, "floor_sprite": services.FLOOR_SPRITE, **overview})


def _int(value, default=-1):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@require_POST
@login_required
def village_place(request):
    char = get_current_player(request)
    if not char:
        return redirect("game:character_create")
    # Empty tiles submit their coordinates as "x,y".
    xy = request.POST.get("xy", "")
    x_str, _, y_str = xy.partition(",")
    messages.info(request, services.place_building(
        char, request.POST.get("type_key", ""), _int(x_str), _int(y_str)))
    return redirect("game:village")


@require_POST
@login_required
def village_upgrade(request):
    char = get_current_player(request)
    if not char:
        return redirect("game:character_create")
    messages.info(request, services.upgrade_building(
        char, _int(request.POST.get("building_id"), 0)))
    return redirect("game:village")


@require_POST
@login_required
def village_train(request):
    """Train soldiers at the Barracks (spends meat)."""
    char = get_current_player(request)
    if not char:
        return redirect("game:character_create")
    r = services.train_troops(request.user, _int(request.POST.get("count"), 0))
    messages.info(request, r.get("error") or r.get("message"))
    return redirect("game:village")


@require_POST
@login_required
def village_raid(request):
    """Lead the army on a raid against an NPC target."""
    char = get_current_player(request)
    if not char:
        return redirect("game:character_create")
    r = services.do_raid(request.user, request.POST.get("target", ""))
    messages.info(request, r.get("error") or r.get("message"))
    return redirect("game:village")


@require_POST
@login_required
def buy(request):
    msg = services.buy_item(request.user, request.POST.get("item_key", ""))
    if _is_ajax(request):
        return JsonResponse({"message": msg, **services.shop_payload(request.user)})
    messages.info(request, msg)
    return redirect("game:shop")


@require_POST
@login_required
def sell(request):
    msg = services.sell_item(request.user, request.POST.get("item_key", ""))
    if _is_ajax(request):
        return JsonResponse({"message": msg, **services.shop_payload(request.user)})
    messages.info(request, msg)
    return redirect("game:shop")


@require_POST
@login_required
def sell_resource(request):
    """Sell village surplus (wood/stone/meat/iron) for gold at the Market."""
    result = services.sell_resources(
        request.user, request.POST.get("resource", ""), request.POST.get("amount", "0"))
    return JsonResponse(result, status=400 if "error" in result else 200)
