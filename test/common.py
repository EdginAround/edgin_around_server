import unittest

import marshmallow

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from edgin_around_api import actions
from src import essentials, events, generator, jobs


class EntityTest(unittest.TestCase):
    """Provides common functionality to all entity tests."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.world = generator.WorldGenerator().generate_basic(100.0)

    def handle_event(
        self,
        entity: essentials.Entity,
        event: events.Event,
    ) -> Tuple[essentials.Task, essentials.Task]:
        """Applies the given event to the given entity and returns old and new task."""

        old_task = entity.get_task()
        entity.handle_event(event)
        new_task = entity.get_task()
        return old_task, new_task

    def assert_events(self, received: List[events.Event], expected: List[events.Event]) -> None:
        """Asserts that the two passed lists of events are equal."""

        self.assertEqual(len(received), len(expected))
        for rec, exp in zip(received, expected):
            self.assert_event(rec, exp)

    def assert_event(self, received: events.Event, expected: events.Event) -> None:
        """Asserts that the two passed events are equal."""

        self.assertEqual(type(received), type(expected))
        if isinstance(received, events.FinishedEvent):
            pass
        else:
            raise Exception(f"Event {type(received).__name__} is not supported by tests yet!")

    def assert_actions(
        self, received: Sequence[actions.Action], expected: Sequence[actions.Action]
    ):
        """Asserts that the two passed lists of actions are equal."""

        self.assertEqual(len(received), len(expected))
        for rec, exp in zip(received, expected):
            self.assert_action(rec, exp)

    def assert_action(self, received: actions.Action, expected: actions.Action) -> None:
        """Asserts that the two passed lists of actions are equal."""

        self.assertEqual(type(received), type(expected))
        if isinstance(received, actions.ConfigurationAction):
            assert isinstance(expected, type(received))  # for mypy
            self.assert_configuration_action(received, expected)
        elif isinstance(received, actions.LocalizeAction):
            assert isinstance(expected, type(received))  # for mypy
            self.assert_localize_action(received, expected)
        elif isinstance(received, actions.MovementAction):
            assert isinstance(expected, type(received))  # for mypy
            self.assert_movement_action(received, expected)
        elif isinstance(received, actions.PickStartAction):
            assert isinstance(expected, type(received))  # for mypy
            self.assert_pick_start_action(received, expected)
        else:
            raise Exception(f"Action {type(received).__name__} is not supported by tests yet!")

    def assert_configuration_action(
        self,
        received: actions.ConfigurationAction,
        expected: actions.ConfigurationAction,
    ) -> None:
        """Asserts that the two passed `configuration` actions are equal."""

        self.assertEqual(received.hero_actor_id, expected.hero_actor_id)

    def assert_localize_action(
        self,
        received: actions.LocalizeAction,
        expected: actions.LocalizeAction,
    ) -> None:
        """Asserts that the two passed `localize` actions are equal."""

        # Position is ignored.
        self.assertEqual(received.actor_id, expected.actor_id)

    def assert_movement_action(
        self,
        received: actions.MovementAction,
        expected: actions.MovementAction,
    ) -> None:
        """Asserts that the two passed `movement` actions are equal."""

        # Bearing is generated randomly. No need to check it.
        self.assertEqual(received.actor_id, expected.actor_id)
        self.assertEqual(received.speed, expected.speed)
        self.assertEqual(received.duration, expected.duration)

    def assert_pick_start_action(
        self,
        received: actions.PickStartAction,
        expected: actions.PickStartAction,
    ) -> None:
        """Asserts that the two passed `pick_start` actions are equal."""

        self.assertEqual(received.who, expected.who)
        self.assertEqual(received.what, expected.what)

    def assert_job(
        self,
        received: Optional[essentials.Job],
        expected: Optional[essentials.Job],
    ) -> None:
        """Asserts that the two passed jobs are equal."""

        self.assertEqual(type(received), type(expected))
        if received is None or expected is None:
            return

        self.assertEqual(received.get_start_delay(), expected.get_start_delay())

        if isinstance(received, jobs.WaitJob):
            assert isinstance(expected, type(received))  # for mypy
            self.assert_wait_job(received, expected)
        elif isinstance(received, jobs.MovementJob):
            assert isinstance(expected, type(received))  # for mypy
            self.assert_movement_job(received, expected)
        else:
            raise Exception(f"Job {type(received).__name__} is not supported by tests yet!")

    def assert_wait_job(self, received: jobs.WaitJob, expected: jobs.WaitJob) -> None:
        """Asserts that the two passed `wait` jobs are equal."""

        self.assertEqual(expected.duration, received.duration)

    def assert_movement_job(self, received: jobs.MovementJob, expected: jobs.MovementJob) -> None:
        """Asserts that the two passed `movement` jobs are equal."""

        # Bearing is generated randomly. No need to check it.
        self.assertEqual(received.entity_id, expected.entity_id)
        self.assertEqual(received.speed, expected.speed)
        self.assertEqual(received.duration, expected.duration)
