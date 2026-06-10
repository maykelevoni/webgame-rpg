"""Pure-engine tests for the army/raid loop: warband power, raid resolution
(win/loss, casualties, hero death) and the village food-upkeep / desertion tick."""
import random

from engine import army, village as v


class FakeRNG:
    """Deterministic stand-in: returns scripted values for uniform()/random()."""
    def __init__(self, uniform=1.0, random_val=1.0):
        self._uniform = uniform
        self._random = random_val

    def uniform(self, a, b):
        return self._uniform

    def random(self):
        return self._random


def _target(defense=50, gold=40, loot=None):
    return army.RaidTarget("camp", "Bandit Camp", defense, gold, loot or {"wood": 10})


def test_warband_power_includes_hero():
    assert army.warband_power(10, 8) == 10 * army.TROOP_POWER + 8
    assert army.warband_power(0, 0) == 0


def test_train_cost():
    assert army.train_cost(5) == 5 * army.TRAIN_MEAT_COST
    assert army.train_cost(0) == 0


def test_strong_raid_wins_with_loot_and_survivors():
    # Overwhelming force: even the worst luck roll (0.8) clears the defense.
    res = army.resolve_raid(50, 30, _target(defense=20, gold=80), FakeRNG(uniform=0.8))
    assert res.win is True
    assert res.loot_gold == 80
    assert res.loot == {"wood": 10}
    assert res.survivors > 0
    assert res.survivors == res.troops_sent - res.troops_lost
    assert res.hero_died is False          # hero never dies on a win


def test_hopeless_raid_loses_no_loot():
    # Tiny warband vs a fortress: even the best luck roll (1.2) can't win.
    res = army.resolve_raid(2, 5, _target(defense=1000), FakeRNG(uniform=1.2, random_val=0.99))
    assert res.win is False
    assert res.loot_gold == 0
    assert res.loot == {}
    assert res.troops_lost >= res.survivors   # heavy casualties when outmatched


def test_hero_can_die_only_when_warband_wiped_and_unlucky():
    tgt = _target(defense=1000)
    # Wiped out (survivors 0) + unlucky roll under 0.60 -> hero falls.
    dead = army.resolve_raid(2, 1, tgt, FakeRNG(uniform=1.2, random_val=0.10))
    assert dead.survivors == 0
    assert dead.hero_died is True
    # Same fight, lucky roll above the threshold -> hero survives the rout.
    alive = army.resolve_raid(2, 1, tgt, FakeRNG(uniform=1.2, random_val=0.90))
    assert alive.hero_died is False


def test_fuzz_invariants_hold():
    rng = random.Random(42)
    for _ in range(500):
        troops = rng.randint(0, 100)
        res = army.resolve_raid(troops, rng.randint(0, 50), _target(rng.randint(5, 400)), rng)
        assert 0 <= res.survivors <= troops
        assert res.troops_lost == troops - res.survivors
        if not res.win:
            assert res.loot_gold == 0 and res.loot == {}
        if res.hero_died:
            assert res.win is False        # the hero only falls in defeat


# --- food upkeep / desertion in the village tick ---------------------------
def _state(meat, troops):
    return v.VillageState(meat=meat, troops=troops, last_tick=0.0)


def test_troops_eat_meat_over_time():
    st = _state(meat=100, troops=10)
    v.tick(st, {}, now=600.0)              # 10 minutes
    eaten = army.UPKEEP_MEAT_PER_MIN * 10 * 10   # 0.15*10 troops*10 min = 15
    assert st.meat == 100 - round(eaten)
    assert st.troops == 10                # well fed, nobody leaves


def test_starvation_makes_troops_desert():
    st = _state(meat=1, troops=20)        # nowhere near enough food
    v.tick(st, {}, now=3600.0)            # an hour
    assert st.meat == 0
    assert st.troops < 20                 # the unfed deserted
    assert st.troops >= 0
