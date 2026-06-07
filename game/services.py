"""The bridge between Django (database) and the pure-Python engine.

Views call these functions. This module is the ONLY place that both touches the
database and builds engine objects — it loads rows, hands the engine plain Python
objects, runs the game logic, then writes the results back. The engine never
imports anything from here.
"""
from __future__ import annotations

import random
from dataclasses import asdict
from pathlib import Path

from django.conf import settings

from engine.character import Character as EngineCharacter
from engine.character import InventoryEntry
from engine.combat import Combat, FLED, LOSE, ONGOING, WIN
from engine.config import EngineConfig
from engine.items import Item as EngineItem
from engine.monsters import Monster as EngineMonster
from engine.monsters import pick_monster
from engine.plugins import load_plugins
from engine.world import EMPTY, MONSTER, TOWN, TREASURE, World

from .identity import get_current_player
from .models import Character, GameConfig, InventoryItem, Item, Monster, PluginState

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
        treasure_count=row.treasure_count, xp_base=row.xp_base,
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
            defense_bonus=row.defense_bonus, icon=row.icon,
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
        ))
    InventoryItem.objects.bulk_create(new_rows)


# --------------------------------------------------------------------------
# High-level actions the views call
# --------------------------------------------------------------------------
def create_character(user, name: str) -> Character:
    """Create a fresh character with starting stats from GameConfig."""
    cfg = load_config()
    model = Character.objects.create(
        owner=user, name=name, level=1, xp=0,
        max_hp=cfg.start_hp, hp=cfg.start_hp,
        base_attack=cfg.start_attack, base_defense=cfg.start_defense,
        gold=cfg.start_gold, map_seed=random.randrange(1_000_000),
        pos_x=cfg.grid_size // 2, pos_y=cfg.grid_size // 2, cleared=[],
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

    Monster tiles show the *actual* monster that will spawn there (varied), not
    one generic icon.
    """
    registry = get_active_plugins()
    spawn = load_spawn_table(registry)
    world = get_world(model, cfg)
    grid = world.render_grid()

    # Decide which monster sits on each monster tile (stable per tile).
    monster_icon = {}
    for (mx, my) in world.monsters:
        mon = pick_monster(spawn, model.level, _tile_rng(model, mx, my))
        monster_icon[(mx, my)] = (mon.icon or GENERIC_MONSTER_SPRITE) if mon else GENERIC_MONSTER_SPRITE

    for row in grid:
        for cell in row:
            x, y = cell["x"], cell["y"]
            cell["deco"] = None
            if cell["is_player"]:
                cell["sprite"] = PLAYER_SPRITE
            elif cell["type"] == "monster":
                cell["sprite"] = monster_icon.get((x, y), GENERIC_MONSTER_SPRITE)
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
    """Move the player one tile and react to whatever is there."""
    model = get_current_player(request)
    cfg = load_config()
    world = get_world(model, cfg)
    result = world.move(direction)
    model.pos_x, model.pos_y = world.player_x, world.player_y

    if result.kind == MONSTER:
        _begin_combat(request, model, (result.x, result.y), cfg)
        model.save()
        return {"kind": "monster"}

    if result.kind == TREASURE:
        reward = _tile_rng(model, result.x, result.y).randint(
            cfg.treasure_gold_min, cfg.treasure_gold_max)
        model.gold += reward
        model.cleared.append([result.x, result.y])
        model.save()
        return {"kind": "treasure", "gold": reward}

    model.save()
    return {"kind": result.kind}  # moved / blocked / town


# ----- combat (in-progress fight is kept in the session) ------------------
def _begin_combat(request, model: Character, tile, cfg: EngineConfig) -> None:
    registry = get_active_plugins()
    spawn = load_spawn_table(registry)
    monster = pick_monster(spawn, model.level, _tile_rng(model, *tile))
    request.session["combat"] = {
        "monster": asdict(monster),
        "monster_hp": monster.max_hp,
        "tile": list(tile),
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
        if data["tile"] not in model.cleared:
            model.cleared.append(data["tile"])     # remove the monster from the map
        save_engine_character(char, model)
        model.save()
        del request.session["combat"]
        # If that was the last monster, unfurl a fresh region to explore.
        fight.area_cleared = _refresh_if_cleared(model, cfg)
    elif fight.outcome == LOSE:
        # Gentle defeat: revive at town, lose half your gold.
        char.gold //= 2
        char.hp = char.max_hp
        save_engine_character(char, model)
        model.pos_x, model.pos_y = get_world(model, cfg).town
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


def use_item(user, item_key: str) -> str:
    model = Character.objects.get(owner=user)
    catalog = load_catalog()
    char = character_to_engine(model, catalog)
    healed = char.use_consumable(item_key)
    save_engine_character(char, model)
    return f"Recovered {healed} HP." if healed else "Nothing happened."


def _refresh_if_cleared(model: Character, cfg: EngineConfig) -> bool:
    """If no monsters remain on the map, roll a brand-new region. Returns True if so."""
    world = get_world(model, cfg)
    if world.monsters:
        return False
    model.map_seed = random.randrange(1_000_000)
    model.cleared = []
    model.pos_x = cfg.grid_size // 2
    model.pos_y = cfg.grid_size // 2
    model.save()
    return True


def leave_town(user) -> None:
    """Step the player out of town onto an adjacent tile (so the town stays visible)."""
    model = Character.objects.get(owner=user)
    cfg = load_config()
    world = get_world(model, cfg)
    tx, ty = world.town
    # Prefer an empty neighbour; fall back to any in-bounds neighbour.
    neighbours = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]
    best = None
    for dx, dy in neighbours:
        nx, ny = tx + dx, ty + dy
        if not world.in_bounds(nx, ny):
            continue
        if best is None:
            best = (nx, ny)
        if world.tile_type(nx, ny) == EMPTY:
            best = (nx, ny)
            break
    if best:
        model.pos_x, model.pos_y = best
        model.save()


def rest(user) -> str:
    model = Character.objects.get(owner=user)
    cfg = load_config()
    if model.gold < cfg.rest_cost:
        return "Not enough gold to rest."
    model.gold -= cfg.rest_cost
    model.hp = model.max_hp
    model.save()
    return "You rest and recover fully."
