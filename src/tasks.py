import time

from typing import List, Optional, Sequence, cast

from edgin_around_api import actions, actors, craft, defs
from . import essentials, features, events, jobs, state


class CraftTask(essentials.Task):
    CRAFT_DURATION = 1.0  # sec

    def __init__(self, crafter_id: essentials.EntityId, assembly: craft.Assembly) -> None:
        super().__init__()
        self._crafter_id = crafter_id
        self._assembly = assembly
        self._job: Optional[essentials.Job] = None

    def start(self, state: state.State) -> Sequence[actions.Action]:
        crafter = state.get_entity(self._crafter_id)
        if crafter is None:
            return list()

        if not crafter.features.inventory:
            return list()

        if crafter.features.inventory.get_free_hand() is None:
            return list()

        if not state.validate_assembly(self._assembly, crafter.features.inventory.get()):
            return list()

        self._job = jobs.WaitJob(self.CRAFT_DURATION, [events.FinishedEvent(self._crafter_id)])
        return [actions.CraftBeginAction(self._crafter_id)]

    def get_job(self) -> Optional[essentials.Job]:
        return self._job

    def finish(self, state: state.State) -> Sequence[actions.Action]:
        crafter = state.get_entity(self._crafter_id)
        if crafter is None or crafter.features.inventory is None:
            return [actions.CraftEndAction(self._crafter_id)]

        craft_result = state.craft_entity(self._assembly, crafter.features.inventory.get())
        return [
            actions.ActorCreationAction(craft_result.created),
            actions.ActorDeletionAction(craft_result.deleted),
            actions.InventoryUpdateAction(self._crafter_id, crafter.features.inventory.get()),
            actions.CraftEndAction(self._crafter_id),
        ]


class DieAndDropTask(essentials.Task):
    def __init__(self, dier_id: essentials.EntityId, drops: List[essentials.Entity]) -> None:
        super().__init__()
        self.dier_id = dier_id
        self.drops = drops
        self.job = jobs.DieJob(self.dier_id)

    def start(self, state: state.State) -> Sequence[actions.Action]:
        dier = state.get_entity(self.dier_id)
        if dier is None:
            return list()

        for drop in self.drops:
            state.add_entity(drop)

        drops = [
            actors.Actor(
                drop.id,
                drop.get_name(),
                drop.position,
            )
            for drop in self.drops
        ]

        return [actions.ActorCreationAction(drops), actions.ActorDeletionAction([self.dier_id])]

    def get_job(self) -> Optional[essentials.Job]:
        return self.job

    def finish(self, state: state.State) -> Sequence[actions.Action]:
        return list()


class IdleTask(essentials.Task):
    def __init__(self, actor_id: essentials.EntityId) -> None:
        super().__init__()
        self.actor_id = actor_id

    def start(self, state: state.State) -> Sequence[actions.Action]:
        return [actions.IdleAction(self.actor_id)]

    def finish(self, state: state.State) -> Sequence[actions.Action]:
        return list()

    def get_job(self) -> Optional[essentials.Job]:
        return None


class InventoryUpdateTask(essentials.Task):
    SWAP_DURATION = 0.01

    def __init__(
        self,
        performer_id: essentials.EntityId,
        hand: defs.Hand,
        inventory_index: int,
        update_variant: defs.UpdateVariant,
    ) -> None:
        super().__init__()
        self.performer_id = performer_id
        self.hand = hand
        self.inventory_index = inventory_index
        self.update_variant = update_variant

    def start(self, state: state.State) -> Sequence[actions.Action]:
        return list()

    def get_job(self) -> Optional[essentials.Job]:
        return jobs.WaitJob(self.SWAP_DURATION, [events.FinishedEvent(self.performer_id)])

    def finish(self, state: state.State) -> Sequence[actions.Action]:
        performer = state.get_entity(self.performer_id)
        if performer is None or performer.features.inventory is None:
            return list()

        inventory = performer.features.inventory.get()
        if self.update_variant == defs.UpdateVariant.SWAP:
            inventory.swap(self.hand, self.inventory_index)
        elif self.update_variant == defs.UpdateVariant.MERGE:
            state.merge_entities(inventory, self.hand, self.inventory_index)
        return [actions.InventoryUpdateAction(self.performer_id, inventory)]


class MotionTask(essentials.Task):
    TIMEOUT = 20.0  # seconds

    def __init__(self, entity_id: defs.ActorId, speed: float, bearing: float) -> None:
        super().__init__()
        self.entity_id = entity_id
        self.speed = speed
        self.bearing = bearing
        self.job = jobs.MotionJob(entity_id, self.speed, self.bearing, self.TIMEOUT, list())

    def start(self, state: state.State) -> Sequence[actions.Action]:
        return [actions.MotionAction(self.entity_id, self.speed, self.bearing, self.TIMEOUT)]

    def get_job(self) -> Optional[essentials.Job]:
        return self.job

    def finish(self, state: state.State) -> Sequence[actions.Action]:
        assert self.job is not None

        entity = state.get_entity(self.entity_id)
        assert entity is not None

        interval = time.monotonic() - self.job.get_prev_call_time()
        entity.move_by(self.speed * interval, self.bearing, state.get_radius())

        position = entity.get_position()
        assert position is not None
        return [actions.LocalizationAction(self.entity_id, position)]


class PickItemTask(essentials.Task):
    PICK_DURATION = 1.0  # sec
    MAX_DISTANCE = 1.0

    def __init__(
        self,
        who_id: essentials.EntityId,
        what_id: Optional[essentials.EntityId],
        hand: defs.Hand,
    ) -> None:
        super().__init__()
        self.who_id = who_id
        self.what_id = what_id
        self.hand = hand
        self.job: Optional[essentials.Job] = None

    def start(self, state: state.State) -> Sequence[actions.Action]:
        if self.what_id is None:
            self.what_id = state.find_closest_delivering_within(
                self.who_id, [features.Claim.CARGO], self.MAX_DISTANCE
            )

        if self.what_id is None:
            return list()

        entity = state.get_entity(self.who_id)
        item = state.get_entity(self.what_id)
        if entity is None or item is None:
            return list()

        distance = state.calculate_distance(entity, item)
        if distance is None or self.MAX_DISTANCE < distance:
            return list()

        if self.what_id is not None:
            self.job = jobs.WaitJob(self.PICK_DURATION, [events.FinishedEvent(self.who_id)])
            return [actions.PickBeginAction(self.who_id, self.what_id)]
        else:
            return list()

    def get_job(self) -> Optional[essentials.Job]:
        return self.job

    def finish(self, state: state.State) -> Sequence[actions.Action]:
        if self.what_id is None:
            return list()

        entity = state.get_entity(self.who_id)
        item = state.get_entity(self.what_id)
        if entity is None or item is None:
            return list()

        if not entity.features.inventory or not item.features.inventorable:
            return list()

        distance = state.calculate_distance(entity, item)
        if distance is None or self.MAX_DISTANCE < distance:
            return list()

        entity.features.inventory.store_entry(self.hand, item.as_info())
        item.features.inventorable.set_stored_by(entity.get_id())
        item.set_position(None)

        result: Sequence[actions.Action] = [
            actions.PickEndAction(self.who_id),
            actions.InventoryUpdateAction(self.who_id, entity.features.inventory.get()),
        ]

        return result


class UseItemTask(essentials.Task):
    MAX_DISTANCE = 1.0

    def __init__(
        self,
        performer_id: essentials.EntityId,
        item_id: essentials.EntityId,
        receiver_id: Optional[essentials.EntityId],
        hand: defs.Hand,
    ) -> None:
        super().__init__()
        self.performer_id = performer_id
        self.item_id = item_id
        self.receiver_id = receiver_id
        self.hand = hand
        self.job: Optional[essentials.Job] = None

    def start(self, state: state.State) -> Sequence[actions.Action]:
        performer = state.get_entity(self.performer_id)
        item = state.get_entity(self.item_id)
        if performer is None or item is None:
            return list()

        claims = item.features.delivery_claims()

        self.receiver_id = (
            self.receiver_id
            if self.receiver_id
            else state.find_closest_absorbing_within(self.performer_id, claims, self.MAX_DISTANCE)
        )

        if self.receiver_id is None:
            return list()

        receiver = state.get_entity(self.receiver_id)
        if receiver is None:
            return list()

        distance = state.calculate_distance(performer, receiver)
        if distance is None or self.MAX_DISTANCE < distance:
            return list()

        claim = receiver.features.get_first_absorbed(claims)

        if claim is None:
            pass

        elif claim is features.Claim.PAIN:
            self.job = jobs.DamageJob(
                self.performer_id,
                self.receiver_id,
                self.item_id,
                self.hand,
                [events.FinishedEvent(self.performer_id)],
            )

        elif claim is features.Claim.FOOD:
            # TODO: Implement eating items.
            pass

        elif claim is features.Claim.CARGO:
            # TODO: Implement giving items.
            pass

        else:
            defs.assert_exhaustive(claim)

        return list()

    def get_job(self) -> Optional[essentials.Job]:
        return self.job

    def finish(self, state: state.State) -> Sequence[actions.Action]:
        return list()


class WalkTask(essentials.Task):
    def __init__(
        self,
        entity_id: defs.ActorId,
        speed: float,
        bearing: float,
        duration: float,
    ) -> None:
        super().__init__()
        self.entity_id = entity_id
        self.speed = speed
        self.bearing = bearing
        self.duration = duration

    def start(self, state: state.State) -> Sequence[actions.Action]:
        return [actions.MotionAction(self.entity_id, self.speed, self.bearing, self.duration)]

    def get_job(self) -> Optional[essentials.Job]:
        return jobs.MotionJob(
            self.entity_id,
            self.speed,
            self.bearing,
            self.duration,
            [events.FinishedEvent(self.entity_id)],
        )

    def finish(self, state: state.State) -> Sequence[actions.Action]:
        entity = state.get_entity(self.entity_id)
        assert entity is not None
        position = entity.get_position()
        assert position is not None
        return [actions.LocalizationAction(self.entity_id, position)]
