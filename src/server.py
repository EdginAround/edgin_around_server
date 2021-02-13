import signal

from . import engine, executor, harbour, gateway, generator


class Server:
    """The main class of the server (backend) side of the game."""

    def __init__(self) -> None:
        self._state = generator.WorldGenerator().generate(100.0)
        self._association = gateway.ClientAssociation()
        self._selector = gateway.Selector()
        self._gateway = gateway.Gateway(self._association, self._selector)
        self._engine = engine.Engine(self._state, self._gateway)
        self._runner = executor.Runner(self._engine)
        self._harbour = harbour.Harbour(self._engine, self._association, self._selector)

    def run(self) -> None:
        try:
            self._harbour.start()
            print("Ready for Edgin'!")
            self._runner.start()

            signal.pause()

        finally:
            self._runner.stop()
            self._harbour.stop()
