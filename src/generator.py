import math, random

from typing import List

from edgin_around_api import geometry
from . import entities, essentials, state


class WorldGenerator:
    def generate_basic(self, radius) -> state.State:
        elevation_function = geometry.Elevation(radius)
        entities: List[essentials.Entity] = list()
        return state.State(elevation_function, entities)

    def generate(self, radius) -> state.State:
        origin = geometry.Point(0.0, 0.0)
        elevation_function = geometry.Elevation(radius)
        elevation_function.add(geometry.Hills(origin))
        elevation_function.add(geometry.Ranges(origin))
        elevation_function.add(geometry.Continents(origin))

        # Entities
        entity_list: List[essentials.Entity] = [
            entities.Axe(1, (0.505 * math.pi, -0.005 * math.pi)),
            entities.Warrior(2, (0.499 * math.pi, 0.001 * math.pi)),
            entities.Warrior(3, (0.498 * math.pi, 0.002 * math.pi)),
            entities.Rocks(4, (0.497 * math.pi, 0.003 * math.pi)),
            entities.Rocks(5, (0.490 * math.pi, 0.010 * math.pi)),
            entities.Gold(6, (0.496 * math.pi, 0.004 * math.pi)),
        ]

        for i in range(7, 50):
            phi = random.uniform(0.4 * math.pi, 0.6 * math.pi)
            theta = random.uniform(-0.1 * math.pi, 0.1 * math.pi)
            entity_list.append(entities.Spruce(i, (phi, theta)))

        return state.State(elevation_function, entity_list)
