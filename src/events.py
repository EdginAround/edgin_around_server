import abc
from dataclasses import dataclass

from typing import Any, Dict, List, Optional

from edgin_around_api import craft, defs, moves


class Event(abc.ABC):
    def __init__(self, receiver_id: defs.ActorId) -> None:
        self._receiver_id = receiver_id

    def get_receiver_id(self) -> defs.ActorId:
        return self._receiver_id


class CraftEvent(Event):
    DEBUG_FIELDS: List[str] = []

    def __init__(
        self,
        receiver_id: defs.ActorId,
        assembly: craft.Assembly,
    ) -> None:
        super().__init__(receiver_id)
        self.assembly = assembly

    @staticmethod
    def from_move(receiver_id: defs.ActorId, move: moves.CraftMove) -> "CraftEvent":
        return CraftEvent(receiver_id, move.assembly)


class DamageEvent(Event):
    DEBUG_FIELDS = ["dealer_id", "receiver_id", "damage_amount", "damage_variant"]

    def __init__(
        self,
        receiver_id: defs.ActorId,
        dealer_id: defs.ActorId,
        damage_amount: float,
        damage_variant: defs.DamageVariant,
    ) -> None:
        super().__init__(receiver_id)
        self.dealer_id = dealer_id
        self.receiver_id = receiver_id
        self.damage_amount = damage_amount
        self.damage_variant = damage_variant


class DisconnectionEvent(Event):
    DEBUG_FIELDS = ["hero_id"]

    def __init__(self, hero_id: defs.ActorId) -> None:
        super().__init__(hero_id)


class FinishedEvent(Event):
    def __init__(self, receiver_id: defs.ActorId) -> None:
        super().__init__(receiver_id)


class HandActivationEvent(Event):
    DEBUG_FIELDS = ["hand", "object_id"]

    def __init__(
        self,
        receiver_id: defs.ActorId,
        hand: defs.Hand,
        object_id: Optional[defs.ActorId],
    ) -> None:
        super().__init__(receiver_id)
        self.hand = hand
        self.object_id = object_id

    @staticmethod
    def from_move(
        receiver_id: defs.ActorId,
        move: moves.HandActivationMove,
    ) -> "HandActivationEvent":
        return HandActivationEvent(receiver_id, move.hand, move.object_id)


class InventoryUpdateEvent(Event):
    DEBUG_FIELDS = ["hand", "inventory_index", "update_variant"]

    def __init__(
        self,
        receiver_id: defs.ActorId,
        hand: defs.Hand,
        inventory_index: int,
        update_variant: defs.UpdateVariant,
    ) -> None:
        super().__init__(receiver_id)
        self.hand = hand
        self.inventory_index = inventory_index
        self.update_variant = update_variant

    @staticmethod
    def from_move(
        receiver_id: defs.ActorId,
        move: moves.InventoryUpdateMove,
    ) -> "InventoryUpdateEvent":
        return InventoryUpdateEvent(
            receiver_id,
            move.hand,
            move.inventory_index,
            move.update_variant,
        )


class ResumeEvent(Event):
    def __init__(self, receiver_id: defs.ActorId) -> None:
        super().__init__(receiver_id)


class MotionStartEvent(Event):
    DEBUG_FIELDS = ["bearing"]

    def __init__(self, receiver_id: defs.ActorId, bearing: float) -> None:
        super().__init__(receiver_id)
        self.bearing = bearing

    @staticmethod
    def from_move(receiver_id: defs.ActorId, move: moves.MotionStartMove) -> "MotionStartEvent":
        return MotionStartEvent(receiver_id, move.bearing)


class MotionStopEvent(Event):
    def __init__(self, receiver_id: defs.ActorId) -> None:
        super().__init__(receiver_id)

    @staticmethod
    def from_move(receiver_id: defs.ActorId, move: moves.MotionStopMove) -> "MotionStopEvent":
        return MotionStopEvent(receiver_id)


_EVENT_CONSTRUCTORS: Dict[type, Any] = {
    moves.CraftMove: CraftEvent.from_move,
    moves.HandActivationMove: HandActivationEvent.from_move,
    moves.InventoryUpdateMove: InventoryUpdateEvent.from_move,
    moves.MotionStartMove: MotionStartEvent.from_move,
    moves.MotionStopMove: MotionStopEvent.from_move,
}


def event_from_move(move: moves.Move, receiver_id: defs.ActorId) -> Optional[Event]:
    """Converts a `Move` into an `Event`."""

    return _EVENT_CONSTRUCTORS[type(move)](receiver_id, move)
