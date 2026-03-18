from __future__ import annotations

from dataclasses import dataclass, field
from heapq import heappop, heappush
from itertools import count
from threading import Condition, Event, Lock, Thread
from typing import Callable, Generic, TypeVar


T = TypeVar("T")


class QueueBusyError(RuntimeError):
    pass


class QueueWaitTimeoutError(RuntimeError):
    pass


@dataclass(order=True)
class _QueuedTask(Generic[T]):
    priority: int
    sequence: int
    fn: Callable[[], T] = field(compare=False)
    started: Event = field(default_factory=Event, compare=False)
    done: Event = field(default_factory=Event, compare=False)
    canceled: bool = field(default=False, compare=False)
    result: T | None = field(default=None, compare=False)
    error: BaseException | None = field(default=None, compare=False)


class TaskRunner:
    def __init__(self, *, name: str, workers: int = 1) -> None:
        self.name = name
        self.workers = max(1, int(workers))
        self._condition = Condition(Lock())
        self._pending: list[_QueuedTask] = []
        self._sequence = count()
        self._started = False
        self._active = 0

    def enqueue(self, fn: Callable[[], object], *, priority: int = 100) -> None:
        task = _QueuedTask(priority=priority, sequence=next(self._sequence), fn=fn)
        self._ensure_started()
        with self._condition:
            heappush(self._pending, task)
            self._condition.notify()

    def submit(
        self,
        fn: Callable[[], T],
        *,
        priority: int = 100,
        max_pending: int | None = None,
        wait_timeout_sec: float | None = None,
    ) -> T:
        task = _QueuedTask[T](priority=priority, sequence=next(self._sequence), fn=fn)
        self._ensure_started()
        with self._condition:
            pending_count = sum(1 for item in self._pending if not item.canceled)
            if max_pending is not None and pending_count >= max_pending:
                raise QueueBusyError(f"{self.name} queue is full.")
            heappush(self._pending, task)
            self._condition.notify()

        if wait_timeout_sec is not None:
            started = task.started.wait(wait_timeout_sec)
            if not started:
                with self._condition:
                    if not task.started.is_set():
                        task.canceled = True
                        raise QueueWaitTimeoutError(f"{self.name} queue wait timed out.")
        else:
            task.started.wait()

        task.done.wait()
        if task.error is not None:
            raise task.error
        return task.result

    def stats(self) -> dict[str, int]:
        with self._condition:
            pending_count = sum(1 for item in self._pending if not item.canceled)
            active_count = self._active
        return {"active": active_count, "pending": pending_count}

    def _ensure_started(self) -> None:
        with self._condition:
            if self._started:
                return
            self._started = True
            for index in range(self.workers):
                worker = Thread(
                    target=self._worker_loop,
                    daemon=True,
                    name=f"{self.name}-worker-{index + 1}",
                )
                worker.start()

    def _worker_loop(self) -> None:
        while True:
            with self._condition:
                while not self._pending:
                    self._condition.wait()
                task = heappop(self._pending)
                if task.canceled:
                    continue
                self._active += 1

            task.started.set()
            try:
                task.result = task.fn()
            except BaseException as error:  # pragma: no cover - worker safety net
                task.error = error
            finally:
                task.done.set()
                with self._condition:
                    self._active = max(0, self._active - 1)
