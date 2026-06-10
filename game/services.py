"""The bridge between Django (database) and the pure-Python engine.

Views call these functions. This module is the ONLY place that both touches the
database and builds engine objects — it loads rows, hands the engine plain Python
objects, runs the game logic, then writes the results back. The engine never
imports anything from here.
"""
from __future__ import annotations

import datetime
import random
import time
from dataclasses import asdict
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from engine.character import Character as EngineCharacter
from engine.character import InventoryEntry
from engine.combat import Combat, FLED, LOSE, ONGOING, WIN
from engine.config import EngineConfig
from engine.items import Item as EngineItem
from engine.monsters import Monster as EngineMonster
from engine.monsters import pick_monster
from engine.plugins import load_plugins
from engine import refine as refine_engine
from engine import army as army_engine
from engine import travel as travel_engine
from engine.world import EMPTY, MOVED, TOWN, TREASURE, World
from engine import maps as maps_engine
from engine.maps import BiomeMap, MapMonster, biome_spec
from engine import village as village_engine
from engine.village import BuildingDef, PlacedBuilding, VillageState

from .identity import get_current_player
from .models import (
    Building, BuildingType, Character, EQUIP_SLOTS, GameConfig, InventoryItem,
    Item, MapArea, MapConnection, Monster, PluginState, Village,
)

PLUGINS_DIR = Path(settings.BASE_DIR) / "plugins"
THEMES_DIR = Path(settings.BASE_DIR) / "game" / "static" / "themes"


# --------------------------------------------------------------------------
# Loading config / catalog / monsters / plugins from the DB into engine data
# --------------------------------------------------------------------------
def load_config() -> EngineConfig:
    """The GameConfig row -> a plain EngineConfig the engine understands."""
    row = GameConfig.load()
    return EngineConfig(
        start_hp=row.start_hp, start_attack=row.start_attack,
        start_defense=row.start_defense, start_gold=row.start_gold,
        grid_size=row.grid_size, monster_count=row.monster_count,
        treasure_count=row.treasure_count, encounter_rate=row.encounter_rate,
        xp_base=row.xp_base,
        xp_growth=row.xp_growth, stat_growth=row.stat_growth,
        rest_cost=row.rest_cost, treasure_gold_min=row.treasure_gold_min,
        treasure_gold_max=row.treasure_gold_max,
    )


def load_catalog() -> dict[str, EngineItem]:
    """All Item rows -> {key: engine Item}."""
    return {
        row.key: EngineItem(
            key=row.key, name=row.name, kind=row.kind, price=row.price,
            heal=row.heal, attack_bonus=row.attack_bonus,
            defense_bonus=row.defense_bonus, icon=row.icon, slot=row.slot,
        )
        for row in Item.objects.all()
    }


def discover_plugin_names() -> list[str]:
    """Names of plugin files in plugins/ (excluding _private and __init__)."""
    if not PLUGINS_DIR.is_dir():
        return []
    return sorted(
        p.stem for p in PLUGINS_DIR.glob("*.py") if not p.stem.startswith("_")
    )


def get_active_plugins():
    """Ensure every discovered plugin has a DB toggle, then load the enabled ones."""
    for name in discover_plugin_names():
        PluginState.objects.get_or_create(name=name, defaults={"enabled": True})
    enabled = set(
        PluginState.objects.filter(enabled=True).values_list("name", flat=True)
    )
    return load_plugins(PLUGINS_DIR, enabled)


def load_spawn_table(registry) -> list[EngineMonster]:
    """Monster rows (+ any monsters added by plugins) -> list of engine Monsters."""
    monsters = [
        EngineMonster(
            key=row.key, name=row.name, max_hp=row.max_hp, attack=row.attack,
            defense=row.defense, gold_reward=row.gold_reward,
            xp_reward=row.xp_reward, min_level=row.min_level, icon=row.icon,
            emoji=row.emoji,
        )
        for row in Monster.objects.all()
    ]
    monsters.extend(registry.monsters)
    return monsters


# --------------------------------------------------------------------------
# Character <-> engine
# --------------------------------------------------------------------------
def character_to_engine(model: Character, catalog: dict[str, EngineItem]) -> EngineCharacter:
    """Build an engine Character (with inventory) from the DB rows."""
    char = EngineCharacter(
        name=model.name, level=model.level, xp=model.xp,
        max_hp=model.max_hp, hp=model.hp, base_attack=model.base_attack,
        base_defense=model.base_defense, gold=model.gold,
    )
    for row in model.inventory.select_related("item").all():
        item = catalog.get(row.item.key)
        if item is None:
            continue
        char.inventory.append(InventoryEntry(
            item=item, quantity=row.quantity,
            equipped=row.equipped, slot=row.slot,
            refine_level=row.refine_level,
        ))
    return char


def save_engine_character(char: EngineCharacter, model: Character) -> None:
    """Write an engine Character's state back to the DB (stats + inventory)."""
    model.level = char.level
    model.xp = char.xp
    model.max_hp = char.max_hp
    model.hp = char.hp
    model.base_attack = char.base_attack
    model.base_defense = char.base_defense
    model.gold = char.gold
    model.save()

    # Simplest correct approach: rewrite the inventory rows from the engine state.
    model.inventory.all().delete()
    item_rows = {i.key: i for i in Item.objects.all()}
    new_rows = []
    for entry in char.inventory:
        item_row = item_rows.get(entry.item.key)
        if item_row is None:
            continue
        new_rows.append(InventoryItem(
            character=model, item=item_row, quantity=entry.quantity,
            equipped=entry.equipped, slot=entry.slot,
            refine_level=entry.refine_level,
        ))
    InventoryItem.objects.bulk_create(new_rows)


# --------------------------------------------------------------------------
# High-level actions the views call
# --------------------------------------------------------------------------
def create_character(user, name: str) -> Character:
    """Create a fresh character with starting stats from GameConfig."""
    cfg = load_config()
    start = MapArea.objects.filter(is_start=True).first() or MapArea.objects.first()
    sx = sy = cfg.grid_size // 2
    if start:
        sx = sy = start.size // 2
    model = Character.objects.create(
        owner=user, name=name, level=1, xp=0,
        max_hp=cfg.start_hp, hp=cfg.start_hp,
        base_attack=cfg.start_attack, base_defense=cfg.start_defense,
        gold=cfg.start_gold, map_seed=random.randrange(1_000_000),
        current_area=start, area_state={}, pos_x=sx, pos_y=sy, cleared=[],
    )
    # A friendly starting kit: a couple of potions.
    potion = Item.objects.filter(key="potion").first()
    if potion:
        InventoryItem.objects.create(character=model, item=potion, quantity=2)
    return model


def get_world(model: Character, cfg: EngineConfig) -> World:
    return World.generate(
        seed=model.map_seed, cfg=cfg, cleared=model.cleared,
        player=(model.pos_x, model.pos_y),
    )


# Sprite names used for the fixed map pieces (Kenney Roguelike pack).
FLOOR_SPRITE = "tile_0005"           # grass
PLAYER_SPRITE = "char_0594"          # the hero
TOWN_SPRITE = "tile_0137"            # door (town entrance)
TREASURE_SPRITE = "tile_0669"        # gold pile
GENERIC_MONSTER_SPRITE = "char_0162"
DECO_SPRITES = ["tile_0342", "tile_0513", "tile_0684"]  # grass with flowers


def _deco_for(x: int, y: int) -> str | None:
    """Deterministically sprinkle some flower tiles onto empty grass for life."""
    h = (x * 73856093) ^ (y * 19349663)
    if h % 5 == 0:
        return DECO_SPRITES[(h // 5) % len(DECO_SPRITES)]
    return None


def build_grid(model: Character, cfg: EngineConfig):
    """Return (grid, size) where each cell carries the sprite to draw.

    Monsters are hidden (random encounters), so only the player, town, and
    treasure show on the map; empty grass gets occasional flower decoration.
    """
    world = get_world(model, cfg)
    grid = world.render_grid()
    for row in grid:
        for cell in row:
            x, y = cell["x"], cell["y"]
            cell["deco"] = None
            if cell["is_player"]:
                cell["sprite"] = PLAYER_SPRITE
            elif cell["type"] == "town":
                cell["sprite"] = TOWN_SPRITE
            elif cell["type"] == "treasure":
                cell["sprite"] = TREASURE_SPRITE
            else:
                cell["sprite"] = None
                cell["deco"] = _deco_for(x, y)
    return grid, world.size


def _tile_rng(model: Character, x: int, y: int) -> random.Random:
    """A stable RNG per (map, tile) so a tile's monster/treasure is consistent."""
    return random.Random(hash((model.map_seed, x, y)) & 0xFFFFFFFF)


def do_move(request, direction: str) -> dict:
    """Move one tile in the current biome map and react to what's there, then let
    nearby monsters take a step toward the player (turn-based pursuit)."""
    model = get_current_player(request)
    area = get_area(model)
    m = build_biome_map(model, area, fresh=False)
    result = m.move(direction)

    # Bumping a monster starts a fight immediately (the player stays put).
    if result.kind == maps_engine.MONSTER:
        _begin_map_encounter(request, model, area, result.data)
        save_area_map(model, area, m)
        return {"kind": "encounter"}

    # Bumping a settlement building uses it (the player stays put, no monster step).
    if result.kind == maps_engine.BUILDING:
        save_area_map(model, area, m)
        return {"kind": "building", "building": result.data}

    # Stepping on an exit transitions to another area (or the town menu).
    if result.kind == maps_engine.CONNECTION:
        save_area_map(model, area, m)
        return _use_connection(model, area, result.data)

    # Resource/chest tiles are NOT harvested here — the client opens a skill
    # mini-game and then calls /play/harvest/ or /play/open-chest/ to collect.
    out: dict = {"kind": "moved"}
    if result.kind == maps_engine.RESOURCE:
        out = {"kind": "resource", "resource": result.data, "x": result.x, "y": result.y}
    elif result.kind == maps_engine.CHEST:
        out = {"kind": "chest", "x": result.x, "y": result.y}
    elif result.kind == maps_engine.BLOCKED:
        out = {"kind": "blocked"}

    # Monsters hold their ground — but stepping next to one makes it pounce. Only
    # check after the player actually moves (bumping a wall shouldn't trigger it).
    moved = result.kind in (maps_engine.MOVED, maps_engine.RESOURCE, maps_engine.CHEST)
    reached = m.aggro_check() if moved else None
    if reached is not None:
        _begin_map_encounter(request, model, area, reached)
        save_area_map(model, area, m)
        return {"kind": "encounter", "after": out["kind"]}

    save_area_map(model, area, m)
    return out


# ----- combat (in-progress fight is kept in the session) ------------------
def _begin_encounter(request, model: Character, cfg: EngineConfig) -> None:
    """Start a random battle with a level-appropriate monster (truly random)."""
    registry = get_active_plugins()
    spawn = load_spawn_table(registry)
    monster = pick_monster(spawn, model.level, random.Random())
    if monster is None:
        return
    request.session["combat"] = {
        "monster": asdict(monster),
        "monster_hp": monster.max_hp,
        "log": [],
    }


def get_combat(request):
    """Reconstruct the current Combat for display (or None if no fight)."""
    data = request.session.get("combat")
    if not data:
        return None, None
    model = get_current_player(request)
    catalog = load_catalog()
    cfg = load_config()
    char = character_to_engine(model, catalog)
    fight = Combat(char, EngineMonster(**data["monster"]), cfg)
    fight.monster_hp = data["monster_hp"]
    fight.log = list(data["log"])
    return fight, model


def combat_action(request, action: str, item_key: str | None = None):
    """Apply one combat action, persist results, return the updated fight."""
    data = request.session.get("combat")
    if not data:
        return None
    model = get_current_player(request)
    catalog = load_catalog()
    cfg = load_config()
    registry = get_active_plugins()
    char = character_to_engine(model, catalog)

    fight = Combat(char, EngineMonster(**data["monster"]), cfg)
    fight.monster_hp = data["monster_hp"]
    fight.log = list(data["log"])
    fight.outcome = ONGOING

    if action == "attack":
        fight.player_attack()
    elif action == "item" and item_key:
        fight.use_item(item_key)
    elif action == "flee":
        fight.flee()

    if fight.outcome == WIN:
        gold, xp = fight.rewards()
        char.gold += gold
        char.gain_xp(xp, cfg)
        registry.run_victory_hooks(char)          # plugin on_victory hooks
        save_engine_character(char, model)
        _clear_defeated_map_monster(model, data.get("map_monster"))
        model.save()
        del request.session["combat"]
    elif fight.outcome == LOSE:
        # Gentle defeat: wake up at the start area, lose half your gold.
        char.gold //= 2
        char.hp = char.max_hp
        save_engine_character(char, model)
        _respawn_at_start(model)
        model.save()
        del request.session["combat"]
    elif fight.outcome == FLED:
        save_engine_character(char, model)
        del request.session["combat"]
    else:  # ongoing — persist HP taken and the running log
        save_engine_character(char, model)
        data["monster_hp"] = fight.monster_hp
        data["log"] = fight.log
        request.session["combat"] = data
        request.session.modified = True

    return fight


# ----- town / shop / equipment -------------------------------------------
# Gold paid per unit when selling village surplus at the Market. Iron is worth more
# (it's the gear material). Admin-tunable later via GameConfig.
RESOURCE_SELL = {"wood": 1, "stone": 1, "meat": 1, "iron": 3}


def shop_payload(user) -> dict:
    """Items, the player's inventory and gold — JSON for the on-map market modal.
    Also includes the village surplus + sell rates for the 'sell resources' panel."""
    model = Character.objects.get(owner=user)
    items = [{"key": i.key, "name": i.name, "kind": i.kind, "price": i.price,
              "heal": i.heal, "attack_bonus": i.attack_bonus,
              "defense_bonus": i.defense_bonus, "sellable": i.sellable,
              "icon": i.icon}
             for i in Item.objects.all()]
    inventory = [{"key": r.item.key, "name": r.item.name, "quantity": r.quantity,
                  "equipped": r.equipped, "price": r.item.price,
                  "sellable": r.item.sellable, "icon": r.item.icon}
                 for r in model.inventory.select_related("item").all()]
    cfg = load_config()
    get_or_create_village(model)
    sync_village(model)                       # accrue production before showing stock
    village = model.village
    village.refresh_from_db()
    return {"gold": model.gold, "hp": model.hp, "max_hp": model.max_hp,
            "rest_cost": cfg.rest_cost, "items": items, "inventory": inventory,
            "resources": {"wood": village.wood, "stone": village.stone,
                          "meat": village.meat, "iron": village.iron},
            "sell_rates": RESOURCE_SELL}


@transaction.atomic
def sell_resources(user, resource: str, amount) -> dict:
    """Sell village surplus (wood/stone/meat/iron) for gold at the Market.
    ``amount`` may be a number or the string 'all'. Returns a fresh shop payload."""
    if resource not in RESOURCE_SELL:
        return {"error": "You can't sell that here."}
    model = Character.objects.get(owner=user)
    sync_village(model)                       # accrue, then read true stock
    village = model.village
    village.refresh_from_db()
    have = getattr(village, resource)
    if str(amount) == "all":
        amount = have
    else:
        try:
            amount = max(0, int(amount))
        except (TypeError, ValueError):
            amount = 0
        amount = min(amount, have)
    if amount <= 0:
        return {"error": f"No {resource} to sell."}
    gold = amount * RESOURCE_SELL[resource]
    setattr(village, resource, have - amount)
    village.save()
    model.gold += gold
    model.save()
    return {"message": f"Sold {amount} {resource} for {gold} gold.", **shop_payload(user)}


def buy_item(user, item_key: str) -> str:
    model = Character.objects.get(owner=user)
    item = Item.objects.filter(key=item_key).first()
    if not item:
        return "That item doesn't exist."
    if model.gold < item.price:
        return "Not enough gold."
    model.gold -= item.price
    model.save()
    row, created = model.inventory.get_or_create(
        item=item, equipped=False, defaults={"quantity": 1})
    if not created:
        row.quantity += 1
        row.save()
    return f"Bought {item.name}."


def sell_item(user, item_key: str) -> str:
    model = Character.objects.get(owner=user)
    row = model.inventory.select_related("item").filter(item__key=item_key).first()
    if not row or not row.item.sellable:
        return "You can't sell that."
    model.gold += row.item.price // 2
    model.save()
    row.quantity -= 1
    if row.quantity <= 0:
        row.delete()
    else:
        row.save()
    return f"Sold {row.item.name}."


def equip_item(user, item_key: str) -> str:
    model = Character.objects.get(owner=user)
    catalog = load_catalog()
    char = character_to_engine(model, catalog)
    ok = char.equip(item_key)
    save_engine_character(char, model)
    return "Equipped." if ok else "You can't equip that."


def unequip_item(user, slot: str) -> str:
    model = Character.objects.get(owner=user)
    char = character_to_engine(model, load_catalog())
    ok = char.unequip(slot)
    save_engine_character(char, model)
    return "Unequipped." if ok else "Nothing to unequip."


# Slot icons for the paper-doll (matches game/models.EQUIP_SLOTS order).
SLOT_EMOJI = {"weapon": "⚔️", "shield": "🛡️", "helmet": "🪖",
              "armor": "🥋", "boots": "🥾", "amulet": "📿"}


def inventory_payload(user) -> dict:
    """The paper-doll (equipped gear per slot) + the carried inventory + live stats —
    JSON for both the Character page and the on-map inventory modal."""
    model = Character.objects.get(owner=user)
    char = character_to_engine(model, load_catalog())
    equipped = {}
    for e in char.inventory:
        if e.equipped and e.item.slot:
            equipped[e.item.slot] = {
                "name": e.item.name, "refine": e.refine_level,
                "atk": e.item.attack_bonus, "def": e.item.defense_bonus}
    slots = [{"slot": key, "label": label, "emoji": SLOT_EMOJI.get(key, "❔"),
              "item": equipped.get(key)} for key, label in EQUIP_SLOTS]
    inventory = [{"id": r.id, "key": r.item.key, "name": r.item.name,
                  "kind": r.item.kind, "slot": r.item.slot, "equipped": r.equipped,
                  "quantity": r.quantity, "refine": r.refine_level,
                  "atk": r.item.attack_bonus, "def": r.item.defense_bonus,
                  "heal": r.item.heal}
                 for r in model.inventory.select_related("item").all()]
    return {"slots": slots, "inventory": inventory, "gold": model.gold,
            "hp": model.hp, "max_hp": model.max_hp,
            "eff_atk": char.effective_attack(), "eff_def": char.effective_defense()}


def use_item(user, item_key: str) -> str:
    model = Character.objects.get(owner=user)
    catalog = load_catalog()
    char = character_to_engine(model, catalog)
    healed = char.use_consumable(item_key)
    save_engine_character(char, model)
    return f"Recovered {healed} HP." if healed else "Nothing happened."


def _refresh_if_cleared(model: Character, cfg: EngineConfig) -> bool:
    """If all treasure has been collected, roll a brand-new region. Returns True if so."""
    world = get_world(model, cfg)
    if world.treasures:
        return False
    model.map_seed = random.randrange(1_000_000)
    model.cleared = []
    model.pos_x = cfg.grid_size // 2
    model.pos_y = cfg.grid_size // 2
    return True


def rest(user) -> str:
    model = Character.objects.get(owner=user)
    cfg = load_config()
    if model.gold < cfg.rest_cost:
        return "Not enough gold to rest."
    model.gold -= cfg.rest_cost
    model.hp = model.max_hp
    model.save()
    return "You rest and recover fully."


# ----- castle smithy (refine gear with iron + gold) -----------------------
def smithy_payload(user) -> dict:
    """The player's refinable gear (+ iron/gold) for the Castle Smithy panel."""
    model = Character.objects.get(owner=user)
    village = get_or_create_village(model)
    sync_village(model)                       # bring iron up to date for display
    village.refresh_from_db()
    gear = []
    for r in model.inventory.select_related("item").exclude(
            item__slot="").order_by("item__name"):
        target = r.refine_level + 1
        at_max = r.refine_level >= refine_engine.MAX_LEVEL
        iron_cost, gold_cost = refine_engine.cost(target)
        gear.append({
            "id": r.id, "name": r.item.name, "icon": r.item.icon,
            "kind": r.item.kind, "equipped": r.equipped,
            "level": r.refine_level, "at_max": at_max,
            "boost": "atk" if r.item.attack_bonus else "def",
            "next_iron": iron_cost, "next_gold": gold_cost,
            "next_chance": round(refine_engine.success_chance(target) * 100),
        })
    return {"iron": village.iron, "gold": model.gold,
            "max_level": refine_engine.MAX_LEVEL, "safe_level": refine_engine.SAFE_LEVEL,
            "gear": gear}


@transaction.atomic
def refine_item(user, inv_id: int) -> dict:
    """Attempt to refine one piece of gear (+1) at the Smithy, spending iron + gold."""
    model = Character.objects.get(owner=user)
    row = model.inventory.select_related("item").filter(id=inv_id).first()
    if not row or not row.item.slot:
        return {"error": "You can only refine equippable gear."}
    sync_village(model)                       # accrue iron, then read it
    village = model.village
    village.refresh_from_db()

    result = refine_engine.attempt(row.refine_level, village.iron, model.gold,
                                   random.Random())
    if result.at_max:
        return {"error": result.message}
    if not result.affordable:
        return {"error": result.message}

    village.iron -= result.iron_cost
    village.save()
    model.gold -= result.gold_cost
    model.save()
    row.refine_level = result.new_level
    row.save()

    char = character_to_engine(model, load_catalog())
    return {
        "success": result.success, "message": result.message,
        "item": row.item.name, "level": result.new_level,
        "iron": village.iron, "gold": model.gold,
        "eff_atk": char.effective_attack(), "eff_def": char.effective_defense(),
        **smithy_payload(user),               # fresh panel to repaint
    }


# ----- castle vault (stash gold safe from the death penalty) --------------
def vault_payload(user) -> dict:
    """Carried vs. stashed gold for the Castle Vault panel."""
    model = Character.objects.get(owner=user)
    return {"gold": model.gold, "vault_gold": model.vault_gold}


def _vault_amount(raw, available: int) -> int:
    """Parse a deposit/withdraw amount: an int, or 'all' = everything available."""
    if str(raw).lower() == "all":
        return available
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 0


@transaction.atomic
def vault_action(user, action: str, amount) -> dict:
    """Move gold between the purse and the Vault. `action` is deposit|withdraw."""
    model = Character.objects.select_for_update().get(owner=user)
    if action == "deposit":
        n = _vault_amount(amount, model.gold)
        if n <= 0:
            return {"error": "Nothing to deposit."}
        if n > model.gold:
            return {"error": "You aren't carrying that much gold."}
        model.gold -= n
        model.vault_gold += n
        msg = f"Stashed {n} 🪙 in the Vault."
    elif action == "withdraw":
        n = _vault_amount(amount, model.vault_gold)
        if n <= 0:
            return {"error": "Nothing to withdraw."}
        if n > model.vault_gold:
            return {"error": "The Vault doesn't hold that much."}
        model.vault_gold -= n
        model.gold += n
        msg = f"Withdrew {n} 🪙 from the Vault."
    else:
        return {"error": "Unknown vault action."}
    model.save(update_fields=["gold", "vault_gold", "updated_at"])
    return {"message": msg, **vault_payload(user)}


# --------------------------------------------------------------------------
# Village / empire <-> engine (see engine/village.py and docs/village-design.md)
# --------------------------------------------------------------------------
def _to_ts(dt: datetime.datetime | None) -> float | None:
    return dt.timestamp() if dt else None


def _from_ts(ts: float | None) -> datetime.datetime | None:
    if ts is None:
        return None
    return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)


def load_building_defs() -> dict[str, BuildingDef]:
    """All BuildingType rows -> {key: engine BuildingDef}."""
    return {
        row.key: BuildingDef(
            key=row.key, name=row.name, category=row.category,
            footprint_w=row.footprint_w, footprint_h=row.footprint_h,
            cost_wood=row.cost_wood, cost_stone=row.cost_stone,
            cost_growth=row.cost_growth, build_seconds=row.build_seconds,
            build_growth=row.build_growth, produces=row.produces,
            production_rate=row.production_rate, storage_bonus=row.storage_bonus,
            max_level=row.max_level,
            requires_longhouse_level=row.requires_longhouse_level,
            max_counts=row.max_counts or {}, icon=row.icon, emoji=row.emoji,
        )
        for row in BuildingType.objects.all()
    }


# A founding stockpile so a brand-new village can raise its first producers
# (you can't build a Lumber Camp with no wood). Tunable later via GameConfig.
STARTING_RESOURCES = {"wood": 120, "stone": 60, "meat": 60}

# The Castle is the shared `city` MapArea you enter from the world map. Unlike the
# Village, its layout is **fixed and authored** (the same for every player) — a set of
# NPC service stations you bump to use, plus a road back to your own Village. These are
# NOT BuildingTypes; they're UI fixtures defined here. (key, emoji, label, x, y)
SETTLEMENT_KEY = "settlement"
CASTLE_SIZE = 7
CASTLE_STATIONS = [
    ("village",  "🛖", "Your Village", 3, 1),
    ("market",   "🏪", "Market",       1, 2),
    ("smithy",   "🔨", "Smithy",       5, 2),
    ("hospital", "🍺", "Tavern",       1, 4),
    ("vault",    "💰", "Vault",        5, 4),
]


def get_or_create_village(character: Character) -> Village:
    """Return the character's Village, founding it (with a starting Town Hall and a
    small stockpile) if new. The Village holds only production buildings — the service
    stations (Market, Smithy, …) live in the shared Castle, not here."""
    village, created = Village.objects.get_or_create(
        character=character, defaults=STARTING_RESOURCES)
    if created:
        lh = BuildingType.objects.filter(key=village_engine.LONGHOUSE).first()
        if lh:
            # The Town Hall stands from day one (level 1), centred on the grid.
            size = village_engine.grid_size_for(1)
            cx = (size - lh.footprint_w) // 2
            cy = (size - lh.footprint_h) // 2
            Building.objects.create(village=village, type=lh, level=1,
                                    pos_x=cx, pos_y=cy)
    return village


def village_to_engine(village: Village) -> VillageState:
    """Build an engine VillageState (with placed buildings) from the DB rows."""
    state = VillageState(
        wood=village.wood, stone=village.stone, meat=village.meat,
        iron=village.iron, troops=village.troops,
        last_tick=village.last_tick.timestamp(),
    )
    for row in village.buildings.select_related("type").all():
        state.buildings.append(PlacedBuilding(
            key=row.type.key, level=row.level, x=row.pos_x, y=row.pos_y,
            build_finish=_to_ts(row.build_finish_at), id=row.id,
        ))
    return state


def save_village(state: VillageState, village: Village) -> None:
    """Write an engine VillageState back to the DB (resources, tick, building levels)."""
    village.wood, village.stone, village.meat = state.wood, state.stone, state.meat
    village.iron = state.iron
    village.troops = state.troops
    village.last_tick = _from_ts(state.last_tick)
    village.save()
    by_id = {b.id: b for b in state.buildings if b.id is not None}
    for row in village.buildings.all():
        b = by_id.get(row.id)
        if not b:
            continue
        row.level = b.level
        row.build_finish_at = _from_ts(b.build_finish)
        row.save()


def sync_village(character: Character) -> tuple[VillageState, dict[str, BuildingDef], list[str]]:
    """Catch the village up to *now* (offline production + finished builds), persist,
    and return the fresh state, the catalog, and the 'while you were away' events."""
    village = get_or_create_village(character)
    defs = load_building_defs()
    state = village_to_engine(village)
    events = village_engine.tick(state, defs, now=time.time())
    save_village(state, village)
    return state, defs, events


@transaction.atomic
def place_building(character: Character, type_key: str, x: int, y: int) -> str:
    """Place a new building at (x, y) and start its first build timer."""
    state, defs, _ = sync_village(character)
    bdef = defs.get(type_key)
    if not bdef:
        return "No such building."
    ok, reason = village_engine.can_place(state, defs, bdef, x, y)
    if not ok:
        return reason
    cost = bdef.cost(1)
    if not village_engine.can_afford(state, cost):
        return "Not enough resources."

    village = character.village
    village.wood -= cost.get(village_engine.WOOD, 0)
    village.stone -= cost.get(village_engine.STONE, 0)
    village.save()
    finish = _from_ts(time.time() + bdef.build_time(1))
    bt = BuildingType.objects.get(key=type_key)
    Building.objects.create(village=village, type=bt, level=0,
                            pos_x=x, pos_y=y, build_finish_at=finish)
    return f"Started building {bdef.name}."


@transaction.atomic
def upgrade_building(character: Character, building_id: int) -> str:
    """Start upgrading an idle, already-built building to its next level."""
    state, defs, _ = sync_village(character)
    row = Building.objects.select_related("type").filter(
        id=building_id, village__character=character).first()
    if not row:
        return "No such building."
    bdef = defs.get(row.type.key)
    if row.build_finish_at is not None:
        return "That building is already busy."
    if row.level >= bdef.max_level:
        return f"{bdef.name} is already at max level."
    target = row.level + 1
    cost = bdef.cost(target)
    if not village_engine.can_afford(state, cost):
        return "Not enough resources."

    village = row.village
    village.wood -= cost.get(village_engine.WOOD, 0)
    village.stone -= cost.get(village_engine.STONE, 0)
    village.save()
    row.build_finish_at = _from_ts(time.time() + bdef.build_time(target))
    row.save()
    return f"Upgrading {bdef.name} to Lv {target}."


# --------------------------------------------------------------------------
# Army / raiding (see engine/army.py and docs/village-design.md)
# --------------------------------------------------------------------------
BARRACKS_KEY = "barracks"

# How many soldiers you may train in one go, per built Barracks level. (The
# Barracks must be built — Lv >= 1 — to train at all.) Balance is tunable here.
TRAIN_BATCH_PER_LEVEL = 5

# Raid targets — NPC camps/villages, tiered by defense. Hardcoded for this slice;
# they're plain data, so moving them to admin-editable rows later is trivial.
RAID_TARGETS = [
    army_engine.RaidTarget("bandit-camp", "Bandit Camp", defense=45,
                           loot_gold=60, loot={"meat": 20, "wood": 20}, emoji="⛺",
                           world_x=64, world_y=34),
    army_engine.RaidTarget("coastal-hamlet", "Coastal Village", defense=120,
                           loot_gold=160, loot={"wood": 40, "stone": 30, "iron": 10}, emoji="🛖",
                           world_x=80, world_y=44),
    army_engine.RaidTarget("rival-jarl", "Enemy Fort", defense=260,
                           loot_gold=380, loot={"stone": 60, "iron": 30}, emoji="🏯",
                           world_x=24, world_y=78),
]
RAID_TARGETS_BY_KEY = {t.key: t for t in RAID_TARGETS}

# How long the hero is laid up after falling in a raid (seconds).
HERO_RECOVERY_SECONDS = 5 * 60


def _has_built_barracks(state: VillageState) -> int:
    """Highest completed Barracks level in the village (0 if none built yet)."""
    return max((b.level for b in state.buildings
                if b.key == BARRACKS_KEY and b.level > 0), default=0)


def hero_recovery(model: Character) -> dict:
    """Is the hero laid up recovering from a raid? Auto-clears once the timer has
    passed. Returns {recovering: bool, seconds_left: int}."""
    until = model.recovering_until
    if not until:
        return {"recovering": False, "seconds_left": 0}
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    if until <= now:
        model.recovering_until = None
        model.save(update_fields=["recovering_until", "updated_at"])
        return {"recovering": False, "seconds_left": 0}
    return {"recovering": True, "seconds_left": int((until - now).total_seconds())}


def army_context(model: Character, state: VillageState) -> dict:
    """Warband state + raid targets (with your power vs. each defense), built from an
    already-synced ``state`` (so the village page can reuse its tick)."""
    barracks_lv = _has_built_barracks(state)
    char = character_to_engine(model, load_catalog())
    hero_atk = char.effective_attack()
    power = army_engine.army_power(state.troops, hero_atk)
    rec = hero_recovery(model)
    targets = [{
        "key": t.key, "name": t.name, "emoji": t.emoji, "defense": t.defense,
        "loot_gold": t.loot_gold, "loot": t.loot,
        "winnable": power >= t.defense,           # rough guide (ignores the luck roll)
    } for t in RAID_TARGETS]
    return {
        "troops": state.troops, "meat": state.meat,
        "hero_attack": hero_atk, "power": power,
        "barracks_level": barracks_lv,
        "train_cost_each": army_engine.TRAIN_MEAT_COST,
        "max_train": barracks_lv * TRAIN_BATCH_PER_LEVEL,
        "upkeep_per_min": round(army_engine.UPKEEP_MEAT_PER_MIN * state.troops, 2),
        "recovering": rec["recovering"], "recovery_seconds": rec["seconds_left"],
        "targets": targets,
    }


def army_payload(user) -> dict:
    """Army context for AJAX callers (syncs the village first)."""
    model = Character.objects.get(owner=user)
    state, _defs, _ev = sync_village(model)
    return army_context(model, state)


@transaction.atomic
def train_troops(user, count: int) -> dict:
    """Train ``count`` soldiers at the Barracks, spending meat. Gated by a built
    Barracks and its level (the training batch cap)."""
    model = Character.objects.select_for_update().get(owner=user)
    state, _defs, _ev = sync_village(model)
    barracks_lv = _has_built_barracks(state)
    if barracks_lv <= 0:
        return {"error": "Build a Barracks first to train soldiers."}
    count = max(0, int(count))
    if count <= 0:
        return {"error": "Train at least one soldier."}
    cap = barracks_lv * TRAIN_BATCH_PER_LEVEL
    if count > cap:
        return {"error": f"Your Barracks (Lv {barracks_lv}) can train at most {cap} at once."}
    cost = army_engine.train_cost(count)
    village = model.village
    village.refresh_from_db()
    if village.meat < cost:
        return {"error": f"Need {cost} 🍖 meat to train {count} (have {village.meat})."}
    village.meat -= cost
    village.troops += count
    village.save(update_fields=["meat", "troops"])
    return {"message": f"Trained {count} soldier{'s' if count != 1 else ''} "
                       f"(−{cost} 🍖).", **army_payload(user)}


@transaction.atomic
def do_raid(user, target_key: str) -> dict:
    """Lead the army on a raid. Applies casualties (only survivors return), loot
    on a win, and — if the hero falls — lays him up to recover."""
    model = Character.objects.select_for_update().get(owner=user)
    rec = hero_recovery(model)
    if rec["recovering"]:
        return {"error": "You're still recovering from your last raid."}
    target = RAID_TARGETS_BY_KEY.get(target_key)
    if not target:
        return {"error": "No such raid target."}
    state, _defs, _ev = sync_village(model)
    if state.troops <= 0:
        return {"error": "You have no soldiers to raid with — train some first."}

    char = character_to_engine(model, load_catalog())
    result = army_engine.resolve_raid(state.troops, char.effective_attack(),
                                      target, random.Random())

    village = model.village
    village.refresh_from_db()
    village.troops = result.survivors
    if result.win:
        model.gold += result.loot_gold
        cap = village_engine.storage_cap(state, _defs)
        for res, amt in result.loot.items():
            setattr(village, res, min(cap, getattr(village, res) + amt))
    village.save()

    if result.hero_died:
        model.gold //= 2                           # same sting as an overworld death
        model.hp = max(1, model.max_hp // 2)
        model.recovering_until = (datetime.datetime.now(tz=datetime.timezone.utc)
                                  + datetime.timedelta(seconds=HERO_RECOVERY_SECONDS))
    model.save()

    return {
        "win": result.win, "hero_died": result.hero_died,
        "troops_sent": result.troops_sent, "survivors": result.survivors,
        "troops_lost": result.troops_lost,
        "loot_gold": result.loot_gold, "loot": result.loot,
        "message": result.message, "gold": model.gold,
        **army_payload(user),
    }


# --------------------------------------------------------------------------
# World Map — the strategic hub (travel to areas / raid targets by distance)
# --------------------------------------------------------------------------
BIOME_EMOJI = {"grass": "🌲", "desert": "🏜️", "ice": "❄️", "dungeon": "🕳️", "city": "🏰"}


def _now_utc() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.timezone.utc)


def _world_nodes() -> dict[str, dict]:
    """Every travel destination keyed by key. Biomes (the explorable areas, minus the
    central Castle) + raid targets. Each carries its World-Map position."""
    nodes: dict[str, dict] = {}
    for a in MapArea.objects.exclude(key=SETTLEMENT_KEY):
        nodes[a.key] = {"key": a.key, "name": a.name, "x": a.world_x, "y": a.world_y,
                        "kind": "biome", "emoji": BIOME_EMOJI.get(a.biome, "🗺️")}
    for t in RAID_TARGETS:
        nodes[t.key] = {"key": t.key, "name": t.name, "x": t.world_x, "y": t.world_y,
                        "kind": "raid", "emoji": t.emoji, "defense": t.defense}
    return nodes


def travel_state(model: Character) -> dict:
    """The hero's current journey, if any."""
    if not model.travel_arrive_at or not model.travel_dest_key:
        return {"traveling": False, "arrived": False, "seconds_left": 0, "dest_key": ""}
    left = (model.travel_arrive_at - _now_utc()).total_seconds()
    return {"traveling": True, "arrived": left <= 0, "seconds_left": max(0, int(left)),
            "dest_key": model.travel_dest_key}


def world_map_payload(user) -> dict:
    """Nodes (with travel times) + the hero's travel/recovery state for the map page."""
    model = Character.objects.get(owner=user)
    nodes = list(_world_nodes().values())
    for n in nodes:
        n["travel_seconds"] = travel_engine.travel_seconds(n["x"], n["y"])
    st = travel_state(model)
    if st["traveling"]:
        st["dest_name"] = _world_nodes().get(st["dest_key"], {}).get("name", "?")
    return {
        "center": list(travel_engine.CENTER),
        "castle": {"key": SETTLEMENT_KEY, "name": "Castle", "x": 50, "y": 50},
        "nodes": nodes,
        "travel": st,
        "recovering": hero_recovery(model)["recovering"],
    }


@transaction.atomic
def start_travel(user, dest_key: str) -> dict:
    """Begin a march to a node; arrival time scales with its distance from the Castle."""
    model = Character.objects.select_for_update().get(owner=user)
    if hero_recovery(model)["recovering"]:
        return {"error": "You're recovering and can't travel yet."}
    st = travel_state(model)
    if st["traveling"] and not st["arrived"]:
        return {"error": "You're already marching somewhere."}
    node = _world_nodes().get(dest_key)
    if not node:
        return {"error": "No such destination."}
    secs = travel_engine.travel_seconds(node["x"], node["y"])
    model.travel_dest_key = dest_key
    model.travel_arrive_at = _now_utc() + datetime.timedelta(seconds=secs)
    model.save(update_fields=["travel_dest_key", "travel_arrive_at"])
    return {"message": f"Marching to {node['name']} — {secs}s.",
            "seconds": secs, "dest_key": dest_key, "dest_name": node["name"]}


@transaction.atomic
def arrive(user) -> dict:
    """Resolve the end of a march: enter a biome, or fight a raid."""
    model = Character.objects.select_for_update().get(owner=user)
    st = travel_state(model)
    if not st["traveling"]:
        return {"error": "You're not travelling."}
    if not st["arrived"]:
        return {"error": f"Still marching ({st['seconds_left']}s left)."}
    dest_key = model.travel_dest_key
    model.travel_dest_key = ""
    model.travel_arrive_at = None
    model.save(update_fields=["travel_dest_key", "travel_arrive_at"])

    if dest_key in RAID_TARGETS_BY_KEY:
        return {"kind": "raid", **do_raid(user, dest_key)}

    area = MapArea.objects.filter(key=dest_key).first()
    if not area:
        return {"error": "That place is gone."}
    model.current_area = area
    model.area_state.setdefault(area.key, {})
    dm = build_biome_map(model, area, fresh=True)
    save_area_map(model, area, dm)
    return {"kind": "area", "area_key": area.key, "area_name": area.name}


def enter_castle(user) -> None:
    """Go home to the Castle (the central hub) — no travel needed."""
    model = Character.objects.get(owner=user)
    castle = MapArea.objects.filter(key=SETTLEMENT_KEY).first()
    if castle:
        model.current_area = castle
        model.save(update_fields=["current_area"])


def build_village_grid(state: VillageState, defs: dict[str, BuildingDef]) -> dict:
    """Cells for the village template: buildings (with footprint span + status) and
    empty placeable tiles, each carrying explicit grid coordinates."""
    now = time.time()
    size = village_engine.grid_size_for(village_engine.longhouse_level(state))
    covered = village_engine.occupied_tiles(state, defs)
    top_left = {(b.x, b.y): b for b in state.buildings}

    cells = []
    for b in state.buildings:
        d = defs.get(b.key)
        if not d:
            continue
        building = b.is_building(now)
        cells.append({
            "kind": "building", "x": b.x, "y": b.y,
            "w": d.footprint_w, "h": d.footprint_h,
            "name": d.name, "level": b.level, "id": b.id,
            "icon": d.icon, "emoji": d.emoji,
            "status": "building" if building else "ready",
            "finish_ms": int((b.build_finish or 0) * 1000) if building else 0,
            "can_upgrade": (not building) and b.level < d.max_level,
        })
    for y in range(size):
        for x in range(size):
            if (x, y) in covered or (x, y) in top_left:
                continue
            cells.append({"kind": "empty", "x": x, "y": y, "w": 1, "h": 1})

    return {"cells": cells, "size": size}


def village_overview(character: Character) -> dict:
    """Everything the village page needs: catches up the tick, then assembles the
    display context (resources, rates, rank, grid, build menu, offline events)."""
    state, defs, events = sync_village(character)
    grid = build_village_grid(state, defs)
    lh = village_engine.longhouse_level(state)
    rates = village_engine.production_rates(state, defs)
    return {
        "events": events,
        "grid": grid,
        "grid_size": grid["size"],
        "palette": buildable_palette(state, defs),
        "wood": state.wood, "stone": state.stone, "meat": state.meat,
        "iron": state.iron,
        "cap": village_engine.storage_cap(state, defs),
        "rate_wood": rates[village_engine.WOOD],
        "rate_stone": rates[village_engine.STONE],
        "rate_meat": rates[village_engine.MEAT],
        "rate_iron": rates[village_engine.IRON],
        "food_net": village_engine.food_balance(state, defs),
        "longhouse_level": lh,
        "rank": village_engine.rank_title(lh),
        "army": army_context(character, state),
    }


# --------------------------------------------------------------------------
# Maps / exploration <-> engine (see engine/maps.py and docs/maps-exploration-design.md)
# --------------------------------------------------------------------------
RESOURCE_EMOJI = {"wood": "🪵", "stone": "🪨", "meat": "🍖"}
CONN_EMOJI = {"mine": "⛏️", "hole": "🕳️", "stairs": "🪜",
              "door": "🚪", "portal": "🌀", "town": "🏠"}


def get_area(model: Character) -> MapArea | None:
    """The character's current area, defaulting to the start area on first play."""
    if model.current_area_id:
        return model.current_area
    start = MapArea.objects.filter(is_start=True).first() or MapArea.objects.first()
    if start:
        model.current_area = start
        model.pos_x = model.pos_y = start.size // 2
        model.save()
    return start


def build_spawn_table(area: MapArea, level: int) -> list[dict]:
    """Monster rows eligible for this biome -> plain dicts the map engine spawns from."""
    out = []
    for r in Monster.objects.all():
        if r.biome and r.biome != area.biome:
            continue
        out.append({"key": r.key, "sight_radius": r.sight_radius,
                    "min_level": r.min_level, "name": r.name, "icon": r.icon})
    return out


def _ser_mon(mm: MapMonster) -> dict:
    return {"key": mm.key, "x": mm.x, "y": mm.y, "sx": mm.sx, "sy": mm.sy,
            "sight_radius": mm.sight_radius, "name": mm.name, "icon": mm.icon}


def _de_mon(d: dict) -> MapMonster:
    return MapMonster(key=d["key"], x=d["x"], y=d["y"], sx=d["sx"], sy=d["sy"],
                      sight_radius=d.get("sight_radius", 4),
                      name=d.get("name", ""), icon=d.get("icon", ""))


def build_castle_map(model: Character, area: MapArea) -> BiomeMap:
    """The Castle: a fixed, authored walkable map of NPC service stations (the same
    for everyone), each a solid tile you bump to use, plus a gate back to the world."""
    builds = [(key, x, y, 1, 1) for (key, _emoji, _label, x, y) in CASTLE_STATIONS]
    gate = area.exits.first()
    m = BiomeMap.settlement(CASTLE_SIZE, builds, str(gate.id) if gate else None)
    # Restore the player's saved tile if it's still walkable; else the gate entry.
    if (model.pos_x, model.pos_y) not in m.buildings and m.walkable(model.pos_x, model.pos_y):
        m.player_x, m.player_y = model.pos_x, model.pos_y
    return m


def build_biome_map(model: Character, area: MapArea, fresh: bool = False) -> BiomeMap:
    """Construct the engine BiomeMap for an area. ``fresh`` (entering an area)
    regenerates monsters at their posts and drops the player at the start tile;
    otherwise it loads the saved live monster positions and the saved player tile."""
    if area.biome == "city":
        return build_castle_map(model, area)
    entry = model.area_state.setdefault(area.key, {})
    seed = entry.get("seed")
    if seed is None:
        seed = area.seed
        entry["seed"] = seed
    spec = biome_spec(area.biome, area.size)
    conn_ids = [str(c.id) for c in area.exits.all()]
    spawn = build_spawn_table(area, model.level)
    m = BiomeMap.generate(seed, spec, entry.get("cleared", []),
                          conn_ids, spawn, model.level)

    stored = entry.get("monsters")
    if fresh or stored is None:
        entry["monsters"] = [_ser_mon(mm) for mm in m.monsters]
        m.player_x, m.player_y = m.start
    else:
        m.monsters = [_de_mon(d) for d in stored]
        if m.walkable(model.pos_x, model.pos_y):
            m.player_x, m.player_y = model.pos_x, model.pos_y
        else:
            m.player_x, m.player_y = m.start
    return m


def save_area_map(model: Character, area: MapArea, m: BiomeMap) -> None:
    entry = model.area_state.setdefault(area.key, {})
    entry["monsters"] = [_ser_mon(mm) for mm in m.monsters]
    model.pos_x, model.pos_y = m.player
    model.save()


def build_castle_grid(model: Character, area: MapArea, m: BiomeMap):
    """Render cells for the Castle: each station is a solid emoji tile you bump to use,
    plus the walkable gate back out to the world."""
    station = {key: (emoji, label) for (key, emoji, label, _x, _y) in CASTLE_STATIONS}
    conn_meta = {str(c.id): (c.kind, c.label or c.get_kind_display())
                 for c in area.exits.all()}
    grid = []
    for y in range(m.size):
        row = []
        for x in range(m.size):
            cell = {"x": x, "y": y, "terrain": "grass",
                    "is_player": (x, y) == m.player,
                    "sprite": None, "emoji": None, "label": None}
            if cell["is_player"]:
                cell["sprite"] = PLAYER_SPRITE
            elif (x, y) in m.buildings:
                emoji, label = station.get(m.buildings[(x, y)], ("🏠", "Building"))
                cell["terrain"] = "building"      # solid structure look
                cell["emoji"] = emoji
                cell["label"] = label
            elif (x, y) in m.conn_tiles:
                kind, label = conn_meta.get(m.conn_tiles[(x, y)], ("door", "Leave"))
                cell["emoji"] = CONN_EMOJI.get(kind, "🚪")
                cell["label"] = label
            row.append(cell)
        grid.append(row)
    return grid, m.size


def build_map_grid(model: Character, area: MapArea):
    """Render cells for the explore template: terrain + visible entities."""
    m = build_biome_map(model, area, fresh=False)
    save_area_map(model, area, m)  # persist the first-visit spawn
    if area.biome == "city":
        return build_castle_grid(model, area, m)
    mon_emoji = {r.key: r.emoji for r in Monster.objects.all() if r.emoji}
    conn_meta = {str(c.id): (c.kind, c.label or c.get_kind_display())
                 for c in area.exits.all()}
    grid = []
    for y in range(m.size):
        row = []
        for x in range(m.size):
            cell = {"x": x, "y": y, "terrain": m.terrain[y][x],
                    "is_player": (x, y) == m.player,
                    "sprite": None, "emoji": None, "label": None}
            if cell["is_player"]:
                cell["sprite"] = PLAYER_SPRITE
            else:
                mon = m.monster_at(x, y)
                if mon is not None:
                    emoji = mon_emoji.get(mon.key)
                    if emoji:
                        cell["emoji"] = emoji
                    else:
                        cell["sprite"] = mon.icon or GENERIC_MONSTER_SPRITE
                    cell["label"] = mon.name
                elif (x, y) in m.conn_tiles:
                    kind, label = conn_meta.get(m.conn_tiles[(x, y)], ("portal", "Exit"))
                    cell["emoji"] = CONN_EMOJI.get(kind, "🌀")
                    cell["label"] = label
                elif (x, y) in m.resources:
                    rtype = m.resources[(x, y)]
                    cell["emoji"] = RESOURCE_EMOJI.get(rtype, "❔")
                    cell["label"] = rtype
                elif (x, y) in m.chests:
                    cell["emoji"] = "📦"
                    cell["label"] = "chest"
            row.append(cell)
        grid.append(row)
    return grid, m.size


def harvest_node(model: Character, *_ignored) -> dict | None:
    """Collect the resource node the player is standing on (the client just plays a
    cracking animation; the yield is a small random amount). None if no node here."""
    area = get_area(model)
    m = build_biome_map(model, area, fresh=False)
    tile = (model.pos_x, model.pos_y)
    rtype = m.resources.get(tile)
    if rtype is None:
        return None
    amount = random.randint(4, 8)
    if rtype in ("wood", "stone", "meat"):
        village = get_or_create_village(model)
        setattr(village, rtype, getattr(village, rtype) + amount)
        village.save()
    model.area_state.setdefault(area.key, {}).setdefault("cleared", []).append(list(tile))
    save_area_map(model, area, m)
    return {"amount": amount, "resource": rtype}


def open_chest_node(model: Character, *_ignored) -> dict | None:
    """Open the chest the player is standing on for some gold. None if no chest."""
    area = get_area(model)
    m = build_biome_map(model, area, fresh=False)
    tile = (model.pos_x, model.pos_y)
    if tile not in m.chests:
        return None
    gold = random.randint(15, 45)
    model.gold += gold
    model.area_state.setdefault(area.key, {}).setdefault("cleared", []).append(list(tile))
    save_area_map(model, area, m)
    return {"gold": gold}


def _begin_map_encounter(request, model: Character, area: MapArea, mon: MapMonster) -> None:
    """Start a fight with a specific map monster, remembering which one (so a win
    can remove it from the map)."""
    template = Monster.objects.filter(key=mon.key).first()
    if not template:
        return
    em = EngineMonster(
        key=template.key, name=template.name, max_hp=template.max_hp,
        attack=template.attack, defense=template.defense,
        gold_reward=template.gold_reward, xp_reward=template.xp_reward,
        min_level=template.min_level, icon=template.icon, emoji=template.emoji)
    request.session["combat"] = {
        "monster": asdict(em),
        "monster_hp": em.max_hp,
        "log": [],
        "map_monster": {"area": area.key, "sx": mon.sx, "sy": mon.sy},
    }


def _clear_defeated_map_monster(model: Character, mm: dict | None) -> None:
    if not mm:
        return
    entry = model.area_state.setdefault(mm["area"], {})
    entry.setdefault("cleared", []).append([mm["sx"], mm["sy"]])
    entry["monsters"] = [d for d in entry.get("monsters", [])
                         if [d.get("sx"), d.get("sy")] != [mm["sx"], mm["sy"]]]


def _respawn_at_start(model: Character) -> None:
    start = MapArea.objects.filter(is_start=True).first() or MapArea.objects.first()
    if start:
        model.current_area = start
        model.pos_x = model.pos_y = start.size // 2
        model.area_state.setdefault(start.key, {})["monsters"] = None


def _use_connection(model: Character, area: MapArea, conn_id: str) -> dict:
    """Follow an exit: route to town, or enter another area (descending regenerates)."""
    conn = MapConnection.objects.filter(
        id=int(conn_id), from_area=area).select_related("to_area").first()
    # A dead-end connection (no destination) is a no-op; any real exit — including
    # the 🏠 settlement link — enters its destination area.
    if not conn or conn.to_area is None:
        return {"kind": "blocked"}
    dest = conn.to_area

    # Where were we when we triggered this exit? (do_move just saved pos onto the
    # exit tile.) If the area we're leaving remembers an entry point *into dest*,
    # walking back should drop us there — not at dest's default start tile.
    src_entry = model.area_state.setdefault(area.key, {})
    return_to = src_entry.pop("return_to", None)
    origin = {"area": area.key, "x": model.pos_x, "y": model.pos_y}

    model.current_area = dest
    entry = model.area_state.setdefault(dest.key, {})
    if conn.descend:
        entry["seed"] = random.randrange(1_000_000)
        entry["cleared"] = []
        entry["monsters"] = None
    entry["return_to"] = origin          # so the way back returns us to this tile

    dm = build_biome_map(model, dest, fresh=True)
    if (return_to and return_to.get("area") == dest.key
            and dm.walkable(return_to["x"], return_to["y"])):
        dm.player_x, dm.player_y = return_to["x"], return_to["y"]
    save_area_map(model, dest, dm)
    return {"kind": "area", "area": dest.name}


def buildable_palette(state: VillageState, defs: dict[str, BuildingDef]) -> list[dict]:
    """The catalog as a buildable menu: cost of a fresh build + affordability/lock."""
    lh = village_engine.longhouse_level(state)
    out = []
    for d in sorted(defs.values(), key=lambda d: (d.requires_longhouse_level, d.name)):
        if d.key == village_engine.LONGHOUSE or d.category == "service":
            continue  # Town Hall + services are pre-built, not placed by the player
        cost = d.cost(1)
        count = village_engine.count_of(state, d.key)
        allowed = d.allowed_count(lh)
        out.append({
            "key": d.key, "name": d.name, "category": d.category,
            "w": d.footprint_w, "h": d.footprint_h, "icon": d.icon,
            "cost_wood": cost.get(village_engine.WOOD, 0),
            "cost_stone": cost.get(village_engine.STONE, 0),
            "locked": lh < d.requires_longhouse_level,
            "requires_lh": d.requires_longhouse_level,
            "affordable": village_engine.can_afford(state, cost),
            "count": count, "max_count": allowed,
            "at_limit": count >= allowed,
        })
    return out
