import time

from typing import List, Optional

from edgin_around_api import actions, defs
from . import essentials, events, state


class DamageJob(essentials.Job):
    DEBUG_FIELDS: List[str] = []
    REPEAT_INTERVAL = 1.0

    def __init__(
        self,
        dealer_id: defs.ActorId,
        receiver_id: defs.ActorId,
        tool_id: defs.ActorId,
        hand: defs.Hand,
        finish_events: List[events.Event],
    ) -> None:
        super().__init__()
        self.dealer_id = dealer_id
        self.receiver_id = receiver_id
        self.tool_id = tool_id
        self.hand = hand
        self.finish_events = finish_events

    def get_start_delay(self) -> float:
        return self.REPEAT_INTERVAL

    def execute(self, state: state.State) -> essentials.JobResult:
        finish = essentials.JobResult(events=self.finish_events)

        dealer = state.get_entity(self.dealer_id)
        if dealer is None or dealer.features.inventory is None:
            return finish

        receiver = state.get_entity(self.receiver_id)
        if receiver is None or receiver.features.damageable is None:
            return finish

        tool = state.get_entity(self.tool_id)
        if tool is None or tool.features.tool_or_weapon is None:
            return finish

        damage_variant = receiver.features.damageable.get_damage_variant()
        damage_amount = tool.features.tool_or_weapon.get_damage(damage_variant)
        event = events.DamageEvent(
            receiver_id=self.receiver_id,
            dealer_id=self.dealer_id,
            damage_amount=damage_amount,
            damage_variant=damage_variant,
        )
        action = actions.DamageAction(
            dealer_id=self.dealer_id,
            receiver_id=self.receiver_id,
            variant=damage_variant,
            hand=self.hand,
        )
        return essentials.JobResult(events=[event], actions=[action], repeat=self.REPEAT_INTERVAL)


class DieJob(essentials.Job):
    def __init__(self, dier_id: defs.ActorId) -> None:
        super().__init__()
        self.dier_id = dier_id

    def get_start_delay(self) -> float:
        return 0.0

    def execute(self, state: state.State) -> essentials.JobResult:
        state.delete_entity(self.dier_id)
        return essentials.JobResult()


class EatJob(essentials.Job):
    def __init__(
        self,
        eater_id: defs.ActorId,
        eater_hand: defs.Hand,
        food_id: defs.ActorId,
        finish_events: List[events.Event],
    ) -> None:
        super().__init__()
        self._eater_id = eater_id
        self._eater_hand = eater_hand
        self._food_id = food_id
        self._finish_events = finish_events

    def get_start_delay(self) -> float:
        return 0.5

    def execute(self, state: state.State) -> essentials.JobResult:
        finish = essentials.JobResult(events=self._finish_events)

        eater = state.get_entity(self._eater_id)
        if eater is None or eater.features.eater is None or eater.features.inventory is None:
            return finish

        food = state.get_entity(self._food_id)
        if food is None or food.features.edible is None:
            return finish

        nutrients = food.features.edible.get_nutrients() * food.features.get_quantity()
        eaten = eater.features.eater.absorb(nutrients)
        if not eaten:
            return essentials.JobResult()

        eater.features.inventory.get().store_entry(self._eater_hand, None)
        stats = eater.features.eater.gather_stats()
        state.delete_entity(self._food_id)

        return essentials.JobResult(
            actions=[
                actions.InventoryUpdateAction(eater.get_id(), eater.features.inventory.get()),
                actions.ActorDeletionAction([self._food_id]),
                actions.StatUpdateAction(eater.get_id(), stats),
            ]
        )


class GrowJob(essentials.Job):
    def __init__(self, grower_id: defs.ActorId, grow_interval: int) -> None:
        super().__init__()
        self.grower_id = grower_id
        self.grow_interval = grow_interval
        self.events: List[events.Event] = [events.GrowEvent(grower_id)]

    def get_start_delay(self) -> float:
        return self.grow_interval

    def execute(self, state: state.State) -> essentials.JobResult:
        return essentials.JobResult(events=self.events, repeat=self.grow_interval)


class HungerDrainJob(essentials.Job):
    DEBUG_FIELDS: List[str] = []
    INTERVAL = 1.0  # sec

    def __init__(self, entity_id: defs.ActorId) -> None:
        super().__init__()
        self.entity_id = entity_id

    def get_start_delay(self) -> float:
        return self.INTERVAL

    def execute(self, state: state.State) -> essentials.JobResult:
        entity = state.get_entity(self.entity_id)
        if entity is None or entity.features.eater is None:
            return essentials.JobResult()

        entity.features.eater.deduce(1.0)
        stats = entity.features.eater.gather_stats()
        action_list: List[actions.Action] = [actions.StatUpdateAction(entity.get_id(), stats)]
        return essentials.JobResult(actions=action_list, repeat=self.INTERVAL)


class MotionJob(essentials.Job):
    DEBUG_FIELDS = ["speed", "bearing", "duration"]
    INTERVAL = 0.1  # second

    def __init__(
        self,
        entity_id: defs.ActorId,
        speed: float,
        bearing: float,
        duration: float,
        finish_events: List[events.Event],
    ) -> None:
        super().__init__()
        self.entity_id = entity_id
        self.speed = speed
        self.bearing = bearing
        self.duration = duration
        self.finish_events = finish_events
        self.start_time = time.monotonic()

    def get_start_delay(self) -> float:
        return self.INTERVAL

    def execute(self, state: state.State) -> essentials.JobResult:
        entity = state.get_entity(self.entity_id)
        if entity is None:
            return essentials.JobResult(events=self.finish_events)

        entity.move_by(self.speed * self.INTERVAL, self.bearing, state.get_radius())

        now = time.monotonic()
        if self.start_time + self.duration < now:
            return essentials.JobResult(events=self.finish_events)
        else:
            return essentials.JobResult(repeat=self.INTERVAL)


class WaitJob(essentials.Job):
    DEBUG_FIELDS = ["duration", "events"]

    def __init__(self, duration: float, events: List[events.Event]) -> None:
        super().__init__()
        self.duration = duration
        self.events = events
        self.next: Optional[WaitJob] = None

    def get_start_delay(self) -> float:
        return self.duration

    def execute(self, state: state.State) -> essentials.JobResult:
        if self.next is not None:
            result = essentials.JobResult(events=self.events, repeat=self.next.duration)
            self.duration = self.next.duration
            self.events = self.next.events
            self.next = self.next.next
            return result

        else:
            return essentials.JobResult(events=self.events, repeat=None)

    def and_then(self, duration: float, events: List[events.Event]) -> "WaitJob":
        self.next = WaitJob(duration, events)
        return self.next
