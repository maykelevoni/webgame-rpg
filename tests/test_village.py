"""Tests for the village engine — costs, placement, the offline tick, ranks.

Pure-Python (no Django, no DB), so these run fast and prove the rules in isolation.
``tick`` takes ``now`` as an argument, so 'time passing' is just arithmetic here.
"""
from engine import village as v
from engine.village import BuildingDef, PlacedBuilding, VillageState


def defs_fixture() -> dict[str, BuildingDef]:
    return {
        "longhouse": BuildingDef("longhouse", "Longhouse", "progression", 2, 2,
                                 cost_wood=50, cost_stone=30, build_seconds=10, max_level=10,
                                 max_counts={"1": 1}),
        "lumber-camp": BuildingDef("lumber-camp", "Lumber Camp", "production", 1, 1,
                                   cost_wood=20, build_seconds=8, produces=v.WOOD,
                                   production_rate=30, max_level=5,
                                   max_counts={"1": 1, "3": 2}),
        "storehouse": BuildingDef("storehouse", "Storehouse", "storage", 2, 2,
                                  cost_wood=40, cost_stone=20, build_seconds=12,
                                  storage_bonus=500, max_level=5, requires_longhouse_level=2,
                                  max_counts={"2": 1}),
    }


def village_with_longhouse(level=1) -> VillageState:
    return VillageState(buildings=[PlacedBuilding("longhouse", level=level, x=2, y=2)])


# --- ranks & grid growth ---------------------------------------------------
def test_rank_titles_climb_with_longhouse_level():
    assert v.rank_title(1) == "Camp"
    assert v.rank_title(3) == "Village"
    assert v.rank_title(5) == "Town"
    assert v.rank_title(8) == "City"
    assert v.rank_title(12) == "Capital"


def test_grid_grows_with_rank_and_caps():
    assert v.grid_size_for(1) == v.GRID_BASE
    assert v.grid_size_for(2) == v.GRID_BASE + 1
    assert v.grid_size_for(999) == v.GRID_CAP


# --- costs & build time ----------------------------------------------------
def test_cost_and_build_time_scale_with_level():
    d = defs_fixture()["lumber-camp"]
    assert d.cost(1)[v.WOOD] == 20
    assert d.cost(2)[v.WOOD] > d.cost(1)[v.WOOD]
    assert d.build_time(2) > d.build_time(1)


# --- placement -------------------------------------------------------------
def test_placement_rejects_out_of_bounds():
    defs = defs_fixture()
    state = village_with_longhouse()
    ok, _ = v.can_place(state, defs, defs["lumber-camp"], v.GRID_BASE, 0)
    assert not ok


def test_placement_rejects_overlap():
    defs = defs_fixture()
    state = village_with_longhouse()  # Longhouse covers (2,2)-(3,3)
    ok, _ = v.can_place(state, defs, defs["lumber-camp"], 2, 2)
    assert not ok
    ok2, _ = v.can_place(state, defs, defs["lumber-camp"], 0, 0)
    assert ok2


def test_placement_respects_longhouse_requirement():
    defs = defs_fixture()
    state = village_with_longhouse(level=1)
    ok, reason = v.can_place(state, defs, defs["storehouse"], 0, 0)
    assert not ok and "Town Hall" in reason
    state2 = village_with_longhouse(level=2)
    ok2, _ = v.can_place(state2, defs, defs["storehouse"], 0, 0)
    assert ok2


def test_build_count_is_limited_by_longhouse_level():
    defs = defs_fixture()
    d = defs["lumber-camp"]
    assert d.allowed_count(1) == 1   # one slot at LH1
    assert d.allowed_count(2) == 1   # still one until LH3
    assert d.allowed_count(3) == 2   # second slot unlocks at LH3
    assert d.allowed_count(9) == 2   # caps at the highest entry

    state = village_with_longhouse(level=1)
    ok, _ = v.can_place(state, defs, d, 0, 0)
    assert ok
    state.buildings.append(PlacedBuilding("lumber-camp", level=1, x=0, y=0))
    ok2, reason = v.can_place(state, defs, d, 1, 0)  # 2nd camp at LH1 -> blocked
    assert not ok2 and "only have 1" in reason


# --- the offline tick ------------------------------------------------------
def test_tick_completes_a_build_when_timer_elapses():
    defs = defs_fixture()
    state = village_with_longhouse()
    state.buildings.append(PlacedBuilding("lumber-camp", level=0, x=0, y=0,
                                          build_finish=100.0))
    state.last_tick = 50.0
    events = v.tick(state, defs, now=150.0)  # past the finish time
    camp = [b for b in state.buildings if b.key == "lumber-camp"][0]
    assert camp.level == 1 and camp.build_finish is None
    assert any("Lumber Camp" in e for e in events)


def test_tick_accrues_production_over_time():
    defs = defs_fixture()
    state = village_with_longhouse()
    state.buildings.append(PlacedBuilding("lumber-camp", level=1, x=0, y=0))
    state.last_tick = 0.0
    v.tick(state, defs, now=120.0)  # 2 minutes at 30/min = 60 wood
    assert state.wood == 60


def test_production_is_capped_by_storage():
    defs = defs_fixture()
    state = village_with_longhouse()
    state.buildings.append(PlacedBuilding("lumber-camp", level=1, x=0, y=0))
    state.last_tick = 0.0
    v.tick(state, defs, now=10_000.0)  # would massively overflow
    assert state.wood == v.BASE_STORAGE  # no Storehouse, so capped at base


def test_unbuilt_building_produces_nothing():
    defs = defs_fixture()
    state = village_with_longhouse()
    state.buildings.append(PlacedBuilding("lumber-camp", level=0, x=0, y=0,
                                          build_finish=999_999.0))
    state.last_tick = 0.0
    v.tick(state, defs, now=120.0)
    assert state.wood == 0  # still under construction
