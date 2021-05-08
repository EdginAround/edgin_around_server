import random, selectors, socket, sys

from typing import Any, Dict, Iterable, List, Optional, Tuple

from edgin_around_api import actors, actions, defs, geometry


class Selector:
    """Wraps `selectors.DefaultSelector`."""

    def __init__(self) -> None:
        self._selector = selectors.DefaultSelector()

    def register(self, sock: socket.socket, data: Any) -> None:
        """Registers the given socket."""

        self._selector.register(sock, selectors.EVENT_READ, data)

    def unregister(self, sock: socket.socket) -> None:
        """Unregisters the given socket."""

        self._selector.unregister(sock)

    def select(self) -> List[Tuple[selectors.SelectorKey, int]]:
        """Wait until some registered file objects become ready."""

        return self._selector.select(timeout=None)


class ClientAssociation:
    """Keeps information about what client is sonnected to which socket."""

    def __init__(self) -> None:
        self._clients: Dict[defs.ActorId, int] = dict()
        self._sockets: Dict[int, socket.socket] = dict()

    def associate_socket(self, client_id: int, sock: socket.socket) -> None:
        """
        Stores information about what entity ID is assigned to the hero controlled by the given
        client.
        """

        self._sockets[client_id] = sock

    def associate_actor(self, client_id: int, actor_id: defs.ActorId) -> None:
        """
        Stores information about what entity ID is assigned to the hero controlled by the given
        client.
        """

        self._clients[actor_id] = client_id

    def disassociate_client(self, client_id: int) -> None:
        """Removes all information related to the given client."""

        actor_id = self._find_actor_for_client(client_id)
        if actor_id is not None:
            del self._clients[actor_id]
            del self._sockets[client_id]

    def disassociate_actor(self, actor_id: defs.ActorId) -> None:
        """Removes all information related to the given client controlling the given hero."""

        client_id = self._clients[actor_id]
        del self._clients[actor_id]
        del self._sockets[client_id]

    def get_sockets(self) -> Iterable[Tuple[int, socket.socket]]:
        """Return an iterable of all connected clients and sockets."""

        return self._sockets.items()

    def generate_client_id(self) -> int:
        """Generates a new client ID."""

        client_ids = self._clients.values()
        while True:
            id = random.randint(0, sys.maxsize)
            if id not in client_ids:
                return id

    def _get_client_for_actor(self, actor_id: defs.ActorId) -> Optional[int]:
        """Returns the client controlling the given hero."""

        return self._clients.get(actor_id, None)

    def _get_socket_for_client(self, client_id: int) -> Optional[socket.socket]:
        """Returns the socket the given client is connected to."""

        return self._sockets.get(client_id, None)

    def _get_socket_for_actor(self, actor_id: defs.ActorId) -> Optional[socket.socket]:
        """Returns the socket the client controlling the given hero is connected to."""

        client_id = self._get_client_for_actor(actor_id)
        if client_id is not None:
            return self._get_socket_for_client(client_id)
        else:
            return None

    def _find_actor_for_client(self, client_id: int) -> Optional[defs.ActorId]:
        """Searches for the hero controlled by the given client."""

        for aid, cid in self._clients.items():
            if cid == client_id:
                return aid
        return None


class Gateway:
    """Provides an interface to send messages back to connected clients."""

    def __init__(self, association: ClientAssociation, selector: Selector) -> None:
        self._association = association
        self._selector = selector

    def associate_actor(self, client_id: int, actor_id: defs.ActorId) -> None:
        """
        Stores information about what entity ID is assigned to the hero controlled by the given
        client.
        """

        self._association.associate_actor(client_id, actor_id)

    def send_configuration(
        self,
        actor_id: defs.ActorId,
        elevation_function: geometry.Elevation,
    ) -> None:
        """Sends the `configuration` message to the specified client."""

        self.send_action(actor_id, actions.ConfigurationAction(actor_id, elevation_function))

    def send_create_actors(self, target_actor_id: defs.ActorId, actors: List[actors.Actor]) -> None:
        """Sends the `create_actors` message to the specified client."""

        self.send_action(target_actor_id, actions.ActorCreationAction(actors))

    def send_action(self, target_actor_id: defs.ActorId, action: actions.Action) -> None:
        """Sends the passed action to the specified client."""

        sock = self._association._get_socket_for_actor(target_actor_id)
        if sock is not None:
            try:
                sock.sendall(f"{action.to_string()}\n".encode())
            except:
                self._selector.unregister(sock)
                self._association.disassociate_actor(target_actor_id)
                sock.close()

    def broadcast_action(self, action: actions.Action) -> None:
        """Sends the passed action to all connected clients client."""

        for client_id, sock in list(self._association.get_sockets()):
            try:
                sock.sendall(f"{action.to_string()}\n".encode())
            except:
                self._selector.unregister(sock)
                self._association.disassociate_client(client_id)
                sock.close()
