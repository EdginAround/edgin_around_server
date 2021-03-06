import socket

from typing import List, Optional


class SocketProcessor:
    """Provides common functionality for all message receivers."""

    def __init__(self, end_of_message=b"\n", chunk_size=1024) -> None:
        self._eom = end_of_message
        self._chunk_size = chunk_size
        self._chunks: List[str] = list()

    def read_messages(self, sock: socket.socket) -> Optional[List[str]]:
        """Reads messages from the socket."""

        EOM = b"\n"
        chunk = b""

        try:
            while EOM not in chunk:
                chunk = sock.recv(self._chunk_size)

                # Iterpret empty data as disconnection
                if not chunk:
                    return None

                self._chunks.append(chunk.decode())

            messages = "".join(self._chunks).split("\n")
            self._chunks = [messages.pop()]
            return messages

        except Exception as e:
            return None
