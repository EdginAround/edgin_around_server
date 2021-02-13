from enum import Enum

from typing import Any, Dict

from edgin_around_api.craft import Ingredient, Material, Recipe


class Sizes(Enum):
    TINY = 1
    SMALL = 5
    MEDIUM = 10
    BIG = 25
    HUGE = 100


RECIPES = [
    Recipe(
        codename="axe",
        description="Axe",
        ingredients=[
            Ingredient(Material.MINERAL, 2),
            Ingredient(Material.WOOD, 1),
        ],
    ),
    Recipe(
        codename="hat",
        description="Hat",
        ingredients=[
            Ingredient(Material.LEATHER, 2),
            Ingredient(Material.ORNAMENT, 1),
            Ingredient(Material.GADGET, 1),
        ],
    ),
]

ENTITIES: Dict[str, Any] = dict()
