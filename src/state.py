import random, sys

from typing import Iterable, List, Optional

from edgin_around_api import actors, craft, defs, inventory, geometry
from . import essentials, features, settings


class CraftResult:
    def __init__(
        self,
        created: List[actors.Actor] = list(),
        deleted: List[defs.ActorId] = list(),
    ) -> None:
        self.created = created
        self.deleted = deleted

    def add_for_creation(self, created: actors.Actor) -> None:
        self.created.append(created)

    def add_for_deletion(self, deleted: defs.ActorId) -> None:
        self.deleted.append(deleted)


class State:
    def __init__(
        self,
        elevation_function: geometry.Elevation,
        entities: List[essentials.Entity],
    ) -> None:
        self.elevation_function = elevation_function
        self.entities = {e.get_id(): e for e in entities}

    def get_entities(self) -> Iterable[essentials.Entity]:
        return self.entities.values()

    def get_entity(self, entity_id: int) -> Optional[essentials.Entity]:
        return self.entities.get(entity_id, None)

    def get_radius(self) -> float:
        return self.elevation_function.get_radius()

    def calculate_distance(
        self,
        entity1: essentials.Entity,
        entity2: essentials.Entity,
    ) -> Optional[float]:
        if entity1.position is not None and entity2.position is not None:
            radius = self.elevation_function.get_radius()
            return entity1.position.great_circle_distance_to(entity2.position, radius)
        else:
            return None

    def find_closest_delivering_within(
        self,
        reference_id: defs.ActorId,
        claim: Iterable[features.Claim],
        max_distance: float,
    ) -> Optional[defs.ActorId]:
        reference = self.get_entity(reference_id)
        if reference is None:
            return None

        min_id = None
        min_distance = 100 * self.get_radius()
        for entity in self.entities.values():
            if entity.get_id() != reference_id and entity.features.deliver(claim):
                distance = self.calculate_distance(reference, entity)
                if distance is not None and distance < min_distance:
                    min_distance = distance
                    min_id = entity.get_id()

        return min_id

    def find_closest_absorbing_within(
        self,
        reference_id: defs.ActorId,
        claims: Iterable[features.Claim],
        max_distance: float,
    ) -> Optional[defs.ActorId]:
        reference = self.get_entity(reference_id)
        if reference is None:
            return None

        min_id = None
        min_distance = 100 * self.get_radius()
        for entity in self.entities.values():
            if entity.get_id() != reference_id and entity.features.absorb(claims):
                distance = self.calculate_distance(reference, entity)
                if distance is not None and distance < min_distance:
                    min_distance = distance
                    min_id = entity.get_id()

        return min_id

    def add_entity(self, entity: essentials.Entity) -> None:
        if entity.get_id() < 0:
            entity.id = self.generate_new_entity_id()
        self.entities[entity.id] = entity

    def delete_entity(self, entity_id: defs.ActorId) -> None:
        del self.entities[entity_id]

    def validate_assembly(self, assembly: craft.Assembly, inventory: inventory.Inventory) -> bool:
        recipe = self._find_recipe_by_codename(assembly.recipe_codename)
        if recipe is None:
            return False

        if not recipe.validate_assembly(assembly):
            return False

        for ingredient, sources in zip(recipe.get_ingredients(), assembly.sources):
            for source in sources:
                entry = inventory.find_entity_with_entity_id(source.actor_id)
                if entry is None:
                    return False

                entity = self.get_entity(entry.id)
                if entity is None:
                    return False

                if not ingredient.match_essence(entity.ESSENCE):
                    return False

                if entity.features.stackable is not None:
                    if entity.features.stackable.get_size() < source.quantity:
                        return False
                else:
                    if source.quantity > 1:
                        return False

        return True

    def craft_entity(self, assembly: craft.Assembly, inventory: inventory.Inventory) -> CraftResult:
        if self.validate_assembly(assembly, inventory):
            return self._craft(assembly, inventory)
        else:
            return CraftResult()

    def _craft(self, assembly: craft.Assembly, inventory: inventory.Inventory) -> CraftResult:
        result = CraftResult()
        recipe = self._find_recipe_by_codename(assembly.recipe_codename)
        assert recipe is not None

        free_hand = inventory.get_free_hand()
        if free_hand is None:
            return result

        # Crafting new entity
        new_entity = self._construct_entity(
            recipe.get_codename(),
            self.generate_new_entity_id(),
            None,
        )
        if new_entity is None:
            return result

        # Deleting ingredients
        for sources in assembly.sources:
            for source in sources:
                entry = inventory.find_entity_with_entity_id(source.actor_id)
                assert entry is not None
                entity = self.get_entity(entry.id)
                assert entity is not None

                if entity.features.stackable is not None:
                    if entity.features.stackable.get_size() == source.quantity:
                        inventory.remove_with_entity_id(entity.id)
                        result.add_for_deletion(entity.id)
                        self.delete_entity(entity.id)
                    else:
                        entity.features.stackable.decrease(source.quantity)
                else:
                    inventory.remove_with_entity_id(entity.id)
                    result.add_for_deletion(entity.id)
                    self.delete_entity(entity.id)

        # Add the new entity
        if new_entity.features.inventorable is not None:
            inventory.store_entry(free_hand, new_entity.as_info())
        else:
            pass  # TODO: place not inventorable entities

        self.add_entity(new_entity)
        result.add_for_creation(new_entity.as_actor())
        return result

    def merge_entities(
        self,
        inventory: inventory.Inventory,
        hand: defs.Hand,
        pocket_index: int,
    ) -> None:
        # Get entries from inventory
        source_entry = inventory.get_hand_entry(hand)
        target_entry = inventory.get_pocket_entry(pocket_index)
        if source_entry is None or target_entry is None:
            return

        # Get the entities stored in the passed invetory entries
        source_entity = self.get_entity(source_entry.id)
        target_entity = self.get_entity(target_entry.id)
        if source_entity is None or target_entity is None:
            return

        # Both entities have to have the same type and be stackable and inventorable
        source_stackable = source_entity.features.stackable
        target_stackable = target_entity.features.stackable
        if source_stackable is None or target_stackable is None:
            return

        source_inventorable = source_entity.features.inventorable
        target_inventorable = target_entity.features.inventorable
        if source_inventorable is None or target_inventorable is None:
            return

        if type(source_entry) != type(target_entry):
            return

        # Calculate new quantities
        item_volume = source_inventorable.get_volume()
        max_target_quantity = target_entry.calc_max_quantity_for_item_volume(item_volume)
        combined_quantity = source_stackable.get_size() + target_stackable.get_size()
        new_target_quantity = min(max_target_quantity, combined_quantity)
        new_source_quantity = combined_quantity - new_target_quantity

        # Update entities and inventory. Remove if necessary.
        target_stackable.set_size(new_target_quantity)
        target_entry.set_quantity(new_target_quantity)

        if new_source_quantity > 0:
            source_stackable.set_size(new_source_quantity)
            source_entry.set_quantity(new_source_quantity)
        else:
            self.delete_entity(source_entry.id)
            inventory.remove_with_entity_id(source_entry.id)

    def _find_recipe_by_codename(self, codename: str) -> Optional[craft.Recipe]:
        for recipe in settings.RECIPES:
            if recipe.get_codename() == codename:
                return recipe
        return None

    def generate_new_entity_id(self) -> defs.ActorId:
        while True:
            id = defs.ActorId(random.randint(0, sys.maxsize))
            if id not in self.entities:
                return id

    def _construct_entity(
        self,
        codename: str,
        id: defs.ActorId,
        position: essentials.EntityPosition,
    ) -> Optional[essentials.Entity]:
        if codename in settings.ENTITIES:
            return settings.ENTITIES[codename](id, position)
        else:
            return None
