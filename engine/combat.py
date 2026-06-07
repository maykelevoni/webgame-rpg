"""Turn-based combat.

One `Combat` object represents a single fight between the player's character and
one monster. Each player action (attack, use an item) is followed by the monster's
response, so a single call advances one full round.

The class only changes the character and its own monster-HP counter — it doesn't
touch the database. The monster *template* is never mutated; we track the
monster's current HP separately so the same template can be reused for later fights.
"""
from __future__ import annotations

import random

from engine.character import Character
from engine.config import EngineConfig
from engine.monsters import Monster

ONGOING = "ongoing"
WIN = "win"
LOSE = "lose"
FLED = "fled"


class Combat:
    def __init__(
        self,
        character: Character,
        monster: Monster,
        cfg: EngineConfig,
        rng: random.Random | None = None,
    ):
        self.character = character
        self.monster = monster
        self.monster_hp = monster.max_hp
        self.cfg = cfg
        self.rng = rng or random.Random()
        self.log: list[str] = []
        self.outcome = ONGOING

    # ----- helpers -------------------------------------------------------
    @staticmethod
    def _damage(attack: int, defense: int) -> int:
        """Damage is attack minus defense, but always at least 1."""
        return max(1, attack - defense)

    @property
    def is_over(self) -> bool:
        return self.outcome != ONGOING

    # ----- player actions (each advances one round) ----------------------
    def player_attack(self) -> None:
        if self.is_over:
            return
        dmg = self._damage(self.character.effective_attack(), self.monster.defense)
        self.monster_hp = max(0, self.monster_hp - dmg)
        self.log.append(f"You hit {self.monster.name} for {dmg}.")
        if self.monster_hp <= 0:
            self.outcome = WIN
            self.log.append(f"You defeated {self.monster.name}!")
            return
        self._enemy_turn()

    def use_item(self, item_key: str) -> bool:
        """Use a consumable as your action. Returns True if it was used."""
        if self.is_over:
            return False
        healed = self.character.use_consumable(item_key)
        if healed <= 0:
            return False  # nothing usable; the turn is not wasted
        self.log.append(f"You use {item_key} and recover {healed} HP.")
        self._enemy_turn()
        return True

    def flee(self) -> None:
        if self.is_over:
            return
        self.outcome = FLED
        self.log.append("You fled the battle.")

    # ----- enemy ---------------------------------------------------------
    def _enemy_turn(self) -> None:
        if self.is_over:
            return
        dmg = self._damage(self.monster.attack, self.character.effective_defense())
        self.character.take_damage(dmg)
        self.log.append(f"{self.monster.name} hits you for {dmg}.")
        if not self.character.is_alive:
            self.outcome = LOSE
            self.log.append("You have been defeated...")

    # ----- result --------------------------------------------------------
    def rewards(self) -> tuple[int, int]:
        """Gold and XP earned. Only meaningful after a win (else 0, 0)."""
        if self.outcome != WIN:
            return (0, 0)
        return (self.monster.gold_reward, self.monster.xp_reward)
