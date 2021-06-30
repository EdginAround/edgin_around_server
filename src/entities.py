import random

from math import pi

from typing import Any, Dict, List, Optional

from edgin_around_api import actions, craft, defs
from . import essentials, events, features, nutrients, settings, tasks


class Rocks(essentials.Entity):
    CODENAME = "rocks"
    ESSENCE = craft.Essence.ROCKS

    def __init__(self, id: defs.ActorId, position: essentials.EntityPosition) -> None:
        super().__init__(id, position)
        self.features.set_inventorable(settings.Sizes.SMALL.value)
        self.features.set_stackable(1)

    def handle_event(self, event: events.Event) -> None:
        pass


class Gold(essentials.Entity):
    CODENAME = "gold"
    ESSENCE = craft.Essence.GOLD

    def __init__(self, id: defs.ActorId, position: essentials.EntityPosition) -> None:
        super().__init__(id, position)
        self.features.set_inventorable(settings.Sizes.SMALL.value)
        self.features.set_stackable(1)

    def handle_event(self, event: events.Event) -> None:
        pass


class RawMeat(essentials.Entity):
    CODENAME = "raw_meat"
    ESSENCE = craft.Essence.MEAT

    def __init__(self, id: defs.ActorId, position: essentials.EntityPosition) -> None:
        super().__init__(id, position)
        self.features.set_edible(nutrients.Nutrients(50))
        self.features.set_inventorable(settings.Sizes.SMALL.value)
        self.features.set_stackable(1)

    def handle_event(self, event: events.Event) -> None:
        pass


class Log(essentials.Entity):
    CODENAME = "log"
    ESSENCE = craft.Essence.LOGS

    def __init__(self, id: defs.ActorId, position: essentials.EntityPosition) -> None:
        super().__init__(id, position)
        self.features.set_inventorable(settings.Sizes.HUGE.value)

    def handle_event(self, event: events.Event) -> None:
        pass


class Axe(essentials.Entity):
    CODENAME = "axe"
    ESSENCE = craft.Essence.TOOL

    def __init__(self, id: defs.ActorId, position: essentials.EntityPosition) -> None:
        super().__init__(id, position)
        self.features.set_inventorable(settings.Sizes.MEDIUM.value)
        self.features.set_tool_or_weapon(
            hit_damage=10,
            chop_damage=100,
            smash_damage=20,
            attack_damage=50,
        )

    def handle_event(self, event: events.Event) -> None:
        pass


class Berry(essentials.Entity):
    CODENAME = "berry"
    ESSENCE = craft.Essence.VEGY

    def __init__(
        self, id: defs.ActorId, position: essentials.EntityPosition, amount: int = 1
    ) -> None:
        super().__init__(id, position)
        self.features.set_edible(nutrients.Nutrients(5))
        self.features.set_inventorable(settings.Sizes.SMALL.value)
        self.features.set_stackable(amount)

    def handle_event(self, event: events.Event) -> None:
        pass


class BerryBush(essentials.Entity):
    CODENAME = "berry_bush"
    ESSENCE = craft.Essence.PLANT

    GROWTH_INTERVAL = 5  # seconds

    STATE_THRESHOLD = 10

    STATE_INITIAL = "default"
    STATE_BARE = "bare"
    STATE_COVERED = "covered"

    def __init__(self, id: defs.ActorId, position: essentials.EntityPosition) -> None:
        super().__init__(id, position)

        self.features.set_performer()
        self.features.set_stateful(self.STATE_INITIAL)
        self.features.set_damageable(
            start_health=100,
            max_health=200,
            damage_variant=defs.DamageVariant.CHOP,
        )
        self.features.set_harvestable(
            start_amount=self.STATE_THRESHOLD - 1,
            min_amount=5,
            max_amount=20,
            grow_amount=1,
            pick_amount=10,
            entity_constructor=lambda amount: self.generate_yields(amount),
        )

    def handle_event(self, event: events.Event) -> None:
        assert self.features.stateful
        assert self.features.harvestable

        if isinstance(event, events.ResumeEvent) or isinstance(event, events.FinishedEvent):
            self.task = tasks.GrowTask(self.get_id(), self.GROWTH_INTERVAL)

        elif isinstance(event, events.GrowEvent):
            current_state = self.features.stateful.get_state_name()
            old_amount, new_amount = self.features.harvestable.grow()

            new_state = self.get_state_for_amount(new_amount)
            if new_state != current_state:
                self.task = tasks.StateChangeTask(self.get_id(), new_state)

        elif isinstance(event, events.PickStartEvent):
            # Berry bush does not prevent players from gathering berries
            pass

        elif isinstance(event, events.PickFinishEvent):
            # Harvesting is handled by the harvester.
            current_state = self.features.stateful.get_state_name()
            new_amount = self.features.harvestable.get_current_amount()
            new_state = self.get_state_for_amount(new_amount)

            if new_state != current_state:
                self.task = tasks.StateChangeTask(self.get_id(), new_state)
            else:
                self.task = tasks.GrowTask(self.get_id(), self.GROWTH_INTERVAL)

        elif isinstance(event, events.DamageEvent):
            assert self.features.damageable
            is_alive = self.features.damageable.handle_damage(event.damage_amount)
            if not is_alive:
                self.task = tasks.DieAndDropTask(self.get_id(), self.generate_drops())

    def generate_yields(self, amount) -> List[essentials.Entity]:
        assert self.position is not None
        if amount > 0:
            return [Berry(defs.UNASSIGNED_ACTOR_ID, self.position, amount)]
        else:
            return list()

    def generate_drops(self) -> List[essentials.Entity]:
        assert self.position is not None
        return [Twig(defs.UNASSIGNED_ACTOR_ID, self.position) for i in range(3)]

    def get_state_for_amount(self, amount) -> str:
        return self.STATE_BARE if amount < self.STATE_THRESHOLD else self.STATE_COVERED


class Spruce(essentials.Entity):
    CODENAME = "spruce"
    ESSENCE = craft.Essence.PLANT

    def __init__(self, id: defs.ActorId, position: essentials.EntityPosition) -> None:
        super().__init__(id, position)
        self.features.set_damageable(
            start_health=200,
            max_health=400,
            damage_variant=defs.DamageVariant.CHOP,
        )

    def handle_event(self, event: events.Event) -> None:
        if isinstance(event, events.DamageEvent):
            assert self.features.damageable
            is_alive = self.features.damageable.handle_damage(event.damage_amount)
            if not is_alive:
                self.task = tasks.DieAndDropTask(self.get_id(), self.generate_drops())

    def generate_drops(self) -> List[essentials.Entity]:
        assert self.position is not None
        return [Log(defs.UNASSIGNED_ACTOR_ID, self.position) for i in range(3)]


class Warrior(essentials.Entity):
    CODENAME = "warrior"
    ESSENCE = craft.Essence.HERO

    def __init__(self, id: defs.ActorId, position: essentials.EntityPosition) -> None:
        super().__init__(id, position)
        self.features.set_performer()
        self.features.set_damageable(
            start_health=200,
            max_health=200,
            damage_variant=defs.DamageVariant.ATTACK,
        )

    def handle_event(self, event: events.Event) -> None:
        if isinstance(event, events.ResumeEvent) or isinstance(event, events.FinishedEvent):
            bearing = random.uniform(-pi, pi)
            self.task = tasks.WalkTask(self.get_id(), speed=1.0, bearing=bearing, duration=1.0)

        elif isinstance(event, events.DamageEvent):
            assert self.features.damageable
            is_alive = self.features.damageable.handle_damage(event.damage_amount)
            if is_alive:
                pass  # TODO: Attack the attacker back.

            else:
                self.task = tasks.DieAndDropTask(self.get_id(), self.generate_drops())

    def generate_drops(self) -> List[essentials.Entity]:
        assert self.position is not None
        return [RawMeat(defs.UNASSIGNED_ACTOR_ID, self.position) for i in range(4)]


class Pirate(essentials.Entity):
    CODENAME = "pirate"
    ESSENCE = craft.Essence.HERO

    def __init__(self, id: defs.ActorId, position: essentials.EntityPosition) -> None:
        self.task: essentials.Task
        super().__init__(id, position)
        self.features.set_inventory()
        self.features.set_eater(max_capacity=100.0, hunger_value=50.0)

    def handle_event(self, event: events.Event) -> None:
        assert self.features.inventory

        if isinstance(event, events.FinishedEvent) or isinstance(event, events.MotionStopEvent):
            self.task = tasks.IdleTask(self.get_id())

        elif isinstance(event, events.MotionStartEvent):
            self.task = tasks.MotionTask(self.get_id(), speed=1.0, bearing=event.bearing)

        elif isinstance(event, events.HandActivationEvent):
            item_id = self.features.inventory.get().get_hand(event.hand)
            if item_id is not None:
                self.task = tasks.UseItemTask(self.get_id(), item_id, event.object_id, event.hand)
            else:
                self.task = tasks.HarvestTask(self.get_id(), event.object_id, event.hand)

        elif isinstance(event, events.InventoryUpdateEvent):
            self.task = tasks.InventoryUpdateTask(
                self.get_id(),
                event.hand,
                event.inventory_index,
                event.update_variant,
            )

        elif isinstance(event, events.CraftEvent):
            self.task = tasks.CraftTask(self.get_id(), event.assembly)

        elif isinstance(event, events.ResumeEvent):
            self.task = tasks.IdleTask(self.get_id())

        elif isinstance(event, events.DisconnectionEvent):
            self.task = tasks.DieAndDropTask(self.get_id(), [])


class Twig(essentials.Entity):
    CODENAME = "twig"
    ESSENCE = craft.Essence.STICKS

    def __init__(self, id: defs.ActorId, position: essentials.EntityPosition) -> None:
        super().__init__(id, position)
        self.features.set_inventorable(settings.Sizes.SMALL.value)

    def handle_event(self, event: events.Event) -> None:
        pass


for klass in [Rocks, Gold, Log, Axe, Spruce, Warrior, Pirate]:
    settings.ENTITIES[klass.CODENAME] = klass
