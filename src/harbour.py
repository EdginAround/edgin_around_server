import json, logging, socket, threading

from typing import Iterable, List

from edgin_around_api import defs, moves
from . import engine, events, gateway, utils

BUFFER_SIZE = 1024


class ServerBroadcaster:
    """Socket event handler responding to clients looking for servers in local networks."""

    def __init__(self) -> None:
        pass

    def process(self, sock: socket.socket, selector: gateway.Selector) -> None:
        """Responds with version of the server."""

        data, addr = sock.recvfrom(BUFFER_SIZE)
        response = {"name": "edgin_around", "version": defs.VERSION}
        sock.sendto(json.dumps(response).encode(), addr)


class EventListener:
    """Socket event handler processing game moves from clients."""

    def __init__(
        self, engine: engine.Engine, association: gateway.ClientAssociation, actor_id: defs.ActorId
    ) -> None:
        self._engine = engine
        self._association = association
        self._actor_id = actor_id
        self._processor = utils.SocketProcessor()

    def process(self, sock: socket.socket, selector: gateway.Selector) -> None:
        """Processes received messages."""

        messages = self._processor.read_messages(sock)
        if messages is not None:
            for message in messages:
                self._process_message(message)
        else:
            logging.info(f"Client controlling actor '{self._actor_id}' disconnected")
            selector.unregister(sock)
            self._engine.handle_disconnection(self._actor_id)
            self._association.disassociate_actor(self._actor_id)
            sock.close()

    def _process_message(self, message: str) -> None:
        """Processes one message and passes it to the `Engine`."""

        move = moves.move_from_json_string(message)
        if move is None:
            return

        event = events.event_from_move(move, self._actor_id)
        if event is None:
            return

        self._engine.handle_event(event)


class EventAcceptor:
    """Socket event handler processing new connections from clients."""

    def __init__(self, engine: engine.Engine, association: gateway.ClientAssociation) -> None:
        self._engine = engine
        self._association = association

    def process(self, sock: socket.socket, selector: gateway.Selector) -> None:
        """Processes new connections."""

        connection, client_address = sock.accept()
        client_id = self._association.generate_client_id()
        self._association.associate_socket(client_id, connection)
        actor_id = self._engine.handle_connection(client_id)
        selector.register(connection, EventListener(self._engine, self._association, actor_id))


class Harbour:
    """Manager handling incoming communication from clients."""

    def __init__(
        self,
        engine: engine.Engine,
        association: gateway.ClientAssociation,
        selector: gateway.Selector,
    ) -> None:
        def target() -> None:
            while self._event.is_set():
                events = self._selector.select()
                for key, mask in events:
                    key.data.process(key.fileobj, self._selector)

        self._selector = selector
        self._event = threading.Event()
        self._thread = threading.Thread(target=target)

        self._prepare_broadcast_socket()
        self._prepare_event_socket(engine, association)

    def start(self) -> None:
        """Starts a new processing thread."""

        self._event.set()
        self._thread.start()

    def stop(self) -> None:
        """Stops the processing thread. Waits until the thread finishes."""

        self._event.clear()
        self._thread.join()

    def _prepare_broadcast_socket(self) -> None:
        """Initializes the broadcast socket."""

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", defs.PORT_BROADCAST))

        self._selector.register(sock, ServerBroadcaster())

    def _prepare_event_socket(
        self,
        engine: engine.Engine,
        association: gateway.ClientAssociation,
    ) -> None:
        """Initializes the main game communication (moves and actions) socket."""

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("", defs.PORT_DATA))
        sock.listen()

        self._selector.register(sock, EventAcceptor(engine, association))
