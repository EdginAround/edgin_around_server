import math, time

from typing import Dict, Optional, Union

from edgin_around_api import actions, actors, defs
from . import entities, essentials, events, executor, gateway, jobs, state, tasks


class Engine(executor.Processor):
    def __init__(self, state: state.State, gateway: gateway.Gateway) -> None:
        self.gateway = gateway
        self.state = state

    def start(self, scheduler) -> None:
        self.scheduler = scheduler
        for entity in self.state.get_entities():
            self._handle_entity(entity)

    def run(self, handle: Optional[int], **kwargs) -> None:
        trigger: Union[events.Event, essentials.Job] = kwargs["trigger"]

        if isinstance(trigger, essentials.Job):
            self._handle_job(handle, trigger)

        elif isinstance(trigger, events.Event):
            self._handle_event(trigger)

    def handle_event(self, event: events.Event) -> None:
        self.run(None, trigger=event)

    def handle_connection(self, client_id: int) -> defs.ActorId:
        # TODO: craeate a custom hero
        hero = entities.Pirate(defs.UNASSIGNED_ACTOR_ID, (0.500 * math.pi, 0.000 * math.pi))
        assert hero.features.inventory is not None

        all_actors = [
            actors.Actor(
                entity.id,
                entity.get_name(),
                entity.position,
            )
            for entity in self.state.get_entities()
        ]

        self.state.add_entity(hero)
        self._handle_entity(hero)

        hero_entity_id = hero.get_id()
        self.gateway.associate_actor(client_id, hero_entity_id)
        self.gateway.send_actor_creation(hero_entity_id, all_actors)
        self.gateway.broadcast_actor_creation([hero.as_actor()])
        self.gateway.send_configuration(hero_entity_id, self.state.elevation_function)
        self.gateway.deliver_inventory_update(hero_entity_id, hero.features.inventory.inventory)

        return hero_entity_id

    def handle_disconnection(self, actor_id: defs.ActorId) -> None:
        self.gateway.disassociate_actor(actor_id)
        self._handle_event(events.DisconnectionEvent(actor_id))

    def _handle_job(self, handle: executor.JobHandle, job: essentials.Job) -> None:
        result = job.perform(self.state)

        for action in result.actions:
            self.gateway.broadcast_action(action)

        for event in result.events:
            self.scheduler.enter(None, 0.0, entity_id=event.get_receiver_id(), trigger=event)

        if result.repeat is not None:
            self.scheduler.enter(handle, result.repeat, trigger=job)

    def _handle_event(self, event: events.Event) -> None:
        entity = self.state.get_entity(event.get_receiver_id())
        if entity is None:
            return

        old_task = entity.get_task()
        entity.handle_event(event)
        new_task = entity.get_task()

        if old_task is not new_task:
            for action in old_task.finish(self.state):
                self.gateway.broadcast_action(action)

            for action in new_task.start(self.state):
                self.gateway.broadcast_action(action)

            next_job = new_task.get_job()
            self.scheduler.cancel(handle=entity.get_id())
            if next_job is not None:
                self.scheduler.enter(
                    handle=entity.get_id(),
                    delay=next_job.get_start_delay(),
                    trigger=next_job,
                )

    def _handle_entity(self, entity: essentials.Entity) -> None:
        entity_id = entity.get_id()
        if entity.features.performer is not None:
            self.run(None, trigger=events.ResumeEvent(entity_id))
        if entity.features.eater is not None:
            self.run(None, trigger=jobs.HungerDrainJob(entity_id))
