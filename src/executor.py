import heapq, threading, time

from abc import abstractmethod
from typing import List, Optional


JobHandle = Optional[int]


class Event:
    def __init__(self, handle: JobHandle, moment: float, kwargs):
        self.handle = handle
        self.moment = moment
        self.kwargs = kwargs

    def __eq__(self, other):
        return self.moment == other.moment

    def __lt__(self, other):
        return self.moment < other.moment

    def __le__(self, other):
        return self.moment <= other.moment

    def __gt__(self, other):
        return self.moment > other.moment

    def __ge__(self, other):
        return self.moment >= other.moment


class Scheduler:
    def __init__(self) -> None:
        self._queue: List[Event] = list()
        self._lock = threading.RLock()

    def enter(self, handle: JobHandle, delay: float, **kwargs) -> None:
        """Schedules next callback.

        handle - Identifier of the callback. Pass to `cancel` method to cancel the callback.
            The handle does not have to be unique. If you want to ensure uniqness, use `cancel`
            before to remove old jobs.
        delay - time interval in seconds to wait before executing the job.
        kwargs - parameters passed to the callback.
        """

        moment = time.monotonic() + delay
        event = Event(handle, moment, kwargs)
        with self._lock:
            heapq.heappush(self._queue, event)

    def cancel(self, handle: int):
        with self._lock:
            self._queue[:] = [e for e in self._queue if e.handle != handle]
            heapq.heapify(self._queue)


class Processor:
    @abstractmethod
    def start(self, scheduler: Scheduler) -> None:
        pass

    @abstractmethod
    def run(self, handle: Optional[int], **kwargs) -> None:
        pass


class Runner:
    def __init__(self, processor: Processor) -> None:
        def target() -> None:
            scheduler = Scheduler()
            processor.start(scheduler)
            while self._event.is_set():
                with scheduler._lock:
                    if len(scheduler._queue) < 1:
                        break
                    event = scheduler._queue[0]
                    delay = event.moment - time.monotonic()
                    if delay < 0:
                        heapq.heappop(scheduler._queue)

                if delay < 0:
                    processor.run(event.handle, **event.kwargs)
                else:
                    time.sleep(delay)

        self._event = threading.Event()
        self._thread = threading.Thread(target=target)

    def start(self) -> None:
        self._event.set()
        self._thread.start()

    def stop(self) -> None:
        self._event.clear()
        self._thread.join()
