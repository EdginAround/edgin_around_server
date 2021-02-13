from . import common

from typing import List

from edgin_around_api import actions, defs, geometry
from src import entities, essentials, events, generator, jobs


class HeroTest(common.EntityTest):
    def test_resume(self) -> None:
        hero = entities.Pirate(0, (0.0, 0.0))
        self.world.add_entity(hero)

        old, new = self.handle_event(hero, events.ResumeEvent(hero.get_id()))
        self.assertTrue(isinstance(old, essentials.IdleTask))
        self.assertTrue(isinstance(new, essentials.IdleTask))
        self.assertEqual(old.finish(self.world), list())
        self.assertEqual(new.get_job(), None)
        self.assertEqual(new.start(self.world), list())

    def test_movement(self) -> None:
        expected_initial: List[actions.Action]

        bearing = 0.0
        max_duration = 20.0
        speed = 1.0
        ignored_location = geometry.Point(0.0, 0.0)

        hero = entities.Pirate(0, (0.0, 0.0))
        self.world.add_entity(hero)
        id = hero.get_id()

        old, new = self.handle_event(hero, events.StartMotionEvent(id, bearing))
        self.assertIsNot(old, new)

        expected_initial = [actions.MovementAction(id, speed, bearing, max_duration)]
        expected_job = jobs.MovementJob(id, speed, bearing, max_duration, list())
        self.assert_actions(old.finish(self.world), list())
        self.assert_actions(new.start(self.world), expected_initial)
        self.assert_job(new.get_job(), expected_job)

        old, new = self.handle_event(hero, events.StopEvent(id))
        self.assertIsNot(old, new)

        expected_initial = [actions.LocalizeAction(id, ignored_location)]
        self.assert_actions(old.finish(self.world), expected_initial)
        self.assert_actions(new.start(self.world), list())
        self.assert_job(new.get_job(), None)

    def test_picking(self) -> None:
        pick_timeout = 1.0
        hero = entities.Pirate(defs.UNASSIGNED_ACTOR_ID, (0.0, 0.0))
        far_object = entities.Rocks(defs.UNASSIGNED_ACTOR_ID, (0.011, 0.011))
        close_object = entities.Rocks(defs.UNASSIGNED_ACTOR_ID, (0.009, 0.009))

        self.world.add_entity(hero)
        self.world.add_entity(far_object)
        self.world.add_entity(close_object)
        hero_id, far_id, close_id = hero.get_id(), far_object.get_id(), close_object.get_id()
        self.assertNotEqual(hero_id, far_id)
        self.assertNotEqual(hero_id, close_id)
        self.assertNotEqual(close_id, far_id)

        # Try to pick an item that is out of range
        hand_event = events.HandActivationEvent(hero_id, defs.Hand.RIGHT, far_id)
        old, new = self.handle_event(hero, hand_event)
        self.assertIsNot(old, new)

        self.assert_actions(old.finish(self.world), list())
        self.assert_actions(new.start(self.world), list())
        self.assert_job(new.get_job(), None)

        # Try to pick an item that is withing range
        hand_event = events.HandActivationEvent(hero_id, defs.Hand.RIGHT, close_id)
        old, new = self.handle_event(hero, hand_event)
        self.assertIsNot(old, new)

        expected_job = jobs.WaitJob(pick_timeout, list())
        expected_initial = [actions.PickStartAction(who=hero_id, what=close_id)]
        self.assert_actions(old.finish(self.world), list())
        self.assert_actions(new.start(self.world), expected_initial)
        self.assert_job(new.get_job(), expected_job)
