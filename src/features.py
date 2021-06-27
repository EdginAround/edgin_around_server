import random

from typing import TYPE_CHECKING

from enum import Enum
from math import pi

from . import nutrients

if TYPE_CHECKING:
    from . import essentials

from typing import Any, Callable, Final, Iterable, List, Optional, Sequence, Set, Tuple

from edgin_around_api import craft, defs, inventory


class Feature:
    def __init__(self) -> None:
        pass

    def __bool__(self) -> bool:
        return True


class PerformerFeature(Feature):
    def __init__(self) -> None:
        super().__init__()

    def start(self):
        pass


class EdibleFeature(Feature):
    def __init__(self, nutrients: nutrients.Nutrients) -> None:
        super().__init__()
        self._nutrients = nutrients

    def get_nutrients(self) -> nutrients.Nutrients:
        return self._nutrients


class EaterFeature(Feature):
    def __init__(self, max_capacity: float, hunger_value: float) -> None:
        super().__init__()
        self.max_capacity = max_capacity
        self.hunger_value = hunger_value

    def deduce(self, value: float) -> None:
        self.hunger_value = max(self.hunger_value - value, 0.0)

    def absorb(self, nutrients: nutrients.Nutrients) -> bool:
        self.hunger_value += nutrients.hunger
        return True

    def get_hunger(self) -> float:
        return self.hunger_value

    def gather_stats(self) -> defs.Stats:
        return defs.Stats(hunger=self.hunger_value, max_hunger=self.max_capacity)


class ToolOrWeaponFeature(Feature):
    def __init__(
        self,
        hit_damage: float,
        chop_damage: float,
        smash_damage: float,
        attack_damage: float,
    ) -> None:
        super().__init__()
        self.damage = {
            defs.DamageVariant.HIT: hit_damage,
            defs.DamageVariant.CHOP: chop_damage,
            defs.DamageVariant.SMASH: smash_damage,
            defs.DamageVariant.ATTACK: attack_damage,
        }

    def get_damage(self, variant: defs.DamageVariant) -> float:
        return self.damage.get(variant, 0.0)


class DamageableFeature(Feature):
    def __init__(
        self,
        start_health: float,
        max_health: float,
        damage_variant: defs.DamageVariant,
    ) -> None:
        super().__init__()
        self.health = start_health
        self.max_health = max_health
        self.damage_variant = damage_variant

    def get_damage_variant(self) -> defs.DamageVariant:
        return self.damage_variant

    def handle_damage(self, damage_amount: float) -> bool:
        self.health = max(0.0, self.health - damage_amount)
        return self.health != 0.0


class HarvestableFeature(Feature):
    def __init__(
        self,
        start_amount: int,
        min_amount: int,
        max_amount: int,
        grow_amount: int,
        pick_amount: int,
        entity_constructor: Callable[[int], Sequence["essentials.Entity"]],
    ) -> None:
        self._current_amount = start_amount
        self._min_amount = min_amount
        self._max_amount = max_amount
        self._grow_amount = grow_amount
        self._pick_amount = pick_amount
        self._entity_constructor = entity_constructor

    def grow(self) -> Tuple[int, int]:
        old_amount = self._current_amount
        new_amount = self._current_amount + self._grow_amount
        self._current_amount = max(self._min_amount, min(new_amount, self._max_amount))
        return (old_amount, self._current_amount)

    def harvest(self) -> Sequence["essentials.Entity"]:
        new_amount = max(0, self._current_amount - self._pick_amount)
        harvested_amount = max(0, min(self._current_amount - self._min_amount, self._pick_amount))
        self._current_amount = new_amount
        return (self._entity_constructor)(harvested_amount)

    def get_current_amount(self) -> int:
        return self._current_amount


class InventoryFeature(Feature):
    def __init__(self) -> None:
        super().__init__()
        self.inventory = inventory.Inventory()

    def store(
        self,
        hand: defs.Hand,
        id: defs.ActorId,
        essence: craft.Essence,
        current_quantity: int,
        item_volume: int,
        max_volume: int,
        codename: str,
    ) -> None:
        self.inventory.store(hand, id, essence, current_quantity, item_volume, max_volume, codename)

    def store_entry(self, hand: defs.Hand, entry: inventory.EntityInfo) -> None:
        self.inventory.store_entry(hand, entry)

    def get_free_hand(self, prefered=defs.Hand.RIGHT) -> Optional[defs.Hand]:
        return self.inventory.get_free_hand(prefered)

    def get(self) -> inventory.Inventory:
        return self.inventory


class InventorableFeature(Feature):
    def __init__(self, volume: int) -> None:
        super().__init__()
        self.volume = volume
        self.stored_by: Optional[defs.ActorId] = None

    def set_stored_by(self, id: defs.ActorId) -> None:
        self.stored_by = id

    def get_volume(self) -> int:
        return self.volume


class StackableFeature(Feature):
    def __init__(self, stack_size: int) -> None:
        super().__init__()
        self.stack_size = stack_size

    def get_size(self) -> int:
        return self.stack_size

    def increase(self, amount: int) -> None:
        self.stack_size += amount

    def decrease(self, amount: int) -> None:
        self.stack_size -= amount

    def set_size(self, amount: int) -> None:
        self.stack_size = amount


class StatefulFeature(Feature):
    def __init__(self, state_name: str) -> None:
        super().__init__()
        self._state_name = state_name

    def get_state_name(self) -> str:
        return self._state_name

    def set_state_name(self, state_name: str) -> None:
        self._state_name = state_name


class Claim(Enum):
    PAIN = 0
    FOOD = 1
    CARGO = 2
    HARVEST = 3


class Features:
    """Bundles all entity features.

    Features are available only for read. To set during intialisation use `set_*` methods.

    The order of calling the `set_*` methods defines the priority of tasks the entity can perform or
    can be performed on the given entity. E.g. food may prefer to be stored to be eaten.
    """

    def __init__(self) -> None:
        self._delivery_claims: List[Claim] = list()
        self._absorption_claims: Set[Claim] = set()

        self.stateful: Final[Optional[StatefulFeature]] = None
        self.performer: Final[Optional[PerformerFeature]] = None
        self.stackable: Final[Optional[StackableFeature]] = None

        self.tool_or_weapon: Final[Optional[ToolOrWeaponFeature]] = None
        self.damageable: Final[Optional[DamageableFeature]] = None

        self.edible: Final[Optional[EdibleFeature]] = None
        self.eater: Final[Optional[EaterFeature]] = None

        self.inventorable: Final[Optional[InventorableFeature]] = None
        self.inventory: Final[Optional[InventoryFeature]] = None
        self.harvestable: Final[Optional[HarvestableFeature]] = None

    def delivery_claims(self) -> List[Claim]:
        return self._delivery_claims

    def deliver(self, claim: Iterable[Claim]) -> bool:
        for c in claim:
            if claim in self._delivery_claims:
                return True
        return False

    def absorb(self, claims: Iterable[Claim]) -> bool:
        for claim in claims:
            if claim in self._absorption_claims:
                return True
        return False

    def get_first_absorbed(self, claims: Iterable[Claim]) -> Optional[Claim]:
        for claim in claims:
            if claim in self._absorption_claims:
                return claim
        return None

    def set_performer(self) -> None:
        self.performer = PerformerFeature()  # type: ignore[misc]

    def set_tool_or_weapon(
        self,
        hit_damage: float,
        chop_damage: float,
        smash_damage: float,
        attack_damage: float,
    ) -> None:
        self._delivery_claims.append(Claim.PAIN)
        self.tool_or_weapon = ToolOrWeaponFeature(  # type: ignore[misc]
            hit_damage,
            chop_damage,
            smash_damage,
            attack_damage,
        )

    def set_damageable(
        self,
        start_health: float,
        max_health: float,
        damage_variant: defs.DamageVariant,
    ) -> None:
        self._absorption_claims.add(Claim.PAIN)
        self.damageable = DamageableFeature(  # type: ignore[misc]
            start_health,
            max_health,
            damage_variant,
        )

    def set_edible(self, nutrients: nutrients.Nutrients) -> None:
        self._delivery_claims.append(Claim.FOOD)
        self.edible = EdibleFeature(nutrients)  # type: ignore[misc]

    def set_eater(self, max_capacity: float, hunger_value: float) -> None:
        self._absorption_claims.add(Claim.FOOD)
        self.eater = EaterFeature(max_capacity, hunger_value)  # type: ignore[misc]

    def set_inventorable(self, volume: int) -> None:
        self._delivery_claims.append(Claim.CARGO)
        self.inventorable = InventorableFeature(volume)  # type: ignore[misc]

    def set_inventory(self) -> None:
        self._absorption_claims.add(Claim.CARGO)
        self.inventory = InventoryFeature()  # type: ignore[misc]

    def set_harvestable(
        self,
        start_amount: int,
        min_amount: int,
        max_amount: int,
        grow_amount: int,
        pick_amount: int,
        entity_constructor: Callable[[int], Sequence["essentials.Entity"]],
    ) -> None:
        self._absorption_claims.add(Claim.HARVEST)
        self.harvestable = HarvestableFeature(  # type: ignore[misc]
            start_amount,
            min_amount,
            max_amount,
            grow_amount,
            pick_amount,
            entity_constructor,
        )

    def set_stackable(self, amount: int) -> None:
        self.stackable = StackableFeature(amount)  # type: ignore[misc]

    def set_stateful(self, state_name: str) -> None:
        self.stateful = StatefulFeature(state_name)  # type: ignore[misc]

    def get_quantity(self) -> int:
        return self.stackable.get_size() if self.stackable is not None else 1
