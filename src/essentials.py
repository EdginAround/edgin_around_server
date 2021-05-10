import random
import time

from math import pi

from abc import abstractmethod
from typing import List, Optional, Union, Sequence, Tuple, TYPE_CHECKING

from edgin_around_api import actions, actors, craft, defs, geometry, inventory
from . import events, features, settings

if TYPE_CHECKING:
    from . import state


EntityId = int
EntityPosition = Union[geometry.Point, Tuple[float, float], None]


class JobResult(defs.Debugable):
    DEBUG_FIELDS = ["events", "actions", "repeat"]

    def __init__(
        self,
        events: List[events.Event] = list(),
        actions: List[actions.Action] = list(),
        repeat: Optional[float] = None,
    ) -> None:
        self.events = events
        self.actions = actions
        self.repeat = repeat


class Job(defs.Debugable):
    def __init__(self) -> None:
        self._num_calls = 0
        self._prev_call_time = time.monotonic()
        self._conclude = False

    def get_num_calls(self) -> int:
        return self._num_calls

    def get_prev_call_time(self) -> float:
        return self._prev_call_time

    def conclude(self) -> None:
        self._conclude = True

    def should_conclude(self) -> bool:
        return self._conclude

    def perform(self, state: "state.State") -> JobResult:
        result = self.execute(state)
        self._num_calls += 1
        self._prev_call_time = time.monotonic()
        return result

    @abstractmethod
    def get_start_delay(self) -> float:
        pass

    @abstractmethod
    def execute(self, state: "state.State") -> JobResult:
        pass


class Task:
    def __init__(self) -> None:
        self.job: Optional[Job] = None

    def conclude(self) -> None:
        if self.job is not None:
            self.job.conclude()

    @abstractmethod
    def start(self, state: "state.State") -> Sequence[actions.Action]:
        pass

    @abstractmethod
    def finish(self, state: "state.State") -> Sequence[actions.Action]:
        pass

    @abstractmethod
    def get_job(self) -> Optional[Job]:
        pass


class EmptyTask(Task):
    def __init__(self) -> None:
        super().__init__()

    def start(self, state: "state.State") -> Sequence[actions.Action]:
        return list()

    def finish(self, state: "state.State") -> Sequence[actions.Action]:
        return list()

    def get_job(self) -> Optional[Job]:
        return None


class Entity:
    CODENAME = "<void>"
    ESSENCE = craft.Essence.VOID

    def __init__(self, id: defs.ActorId, position: EntityPosition) -> None:
        self.id = id
        self.task: Task = EmptyTask()
        self.features = features.Features()

        self.position: Optional[geometry.Point]
        if isinstance(position, geometry.Point):
            self.position = position
        elif isinstance(position, tuple):
            self.position = geometry.Point(*position)
        else:
            self.position = None

    def get_id(self) -> EntityId:
        return self.id

    def get_name(self) -> str:
        return self.CODENAME

    def get_essence(self) -> craft.Essence:
        return self.ESSENCE

    def get_task(self) -> Task:
        return self.task

    def get_position(self) -> Optional[geometry.Point]:
        return self.position

    def as_actor(self) -> actors.Actor:
        return actors.Actor(self.get_id(), self.get_name(), self.get_position())

    def as_craft_item(self) -> craft.Item:
        quantity = self.features.stackable.get_size() if self.features.stackable is not None else 1
        return craft.Item(self.get_id(), self.get_essence(), quantity)

    def as_info(self) -> inventory.EntityInfo:
        item_volume = (
            self.features.inventorable.get_volume() if self.features.inventorable is not None else 1
        )

        return inventory.EntityInfo(
            self.get_id(),
            self.get_essence(),
            self.features.get_quantity(),
            item_volume,
            settings.Sizes.BIG.value,
            self.get_name(),
        )

    def set_position(self, position: Optional[geometry.Point]):
        self.position = position

    def move_by(self, distance, bearing, radius) -> None:
        if self.position is not None:
            self.position = self.position.moved_by(distance, bearing, radius)

    def __repr__(self) -> str:
        return f"Entity({self.CODENAME}, {self.id})"

    @abstractmethod
    def handle_event(self, event):
        pass
