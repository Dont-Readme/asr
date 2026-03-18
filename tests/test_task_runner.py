from __future__ import annotations

import threading
import time
import unittest

from src.services.task_runner import QueueWaitTimeoutError, TaskRunner


class TaskRunnerTest(unittest.TestCase):
    def test_priority_runner_executes_voice_before_waiting_meeting_task(self) -> None:
        runner = TaskRunner(name="priority-test", workers=1)
        release_blocker = threading.Event()
        blocker_started = threading.Event()
        execution_order: list[str] = []

        def blocker() -> None:
            blocker_started.set()
            release_blocker.wait(timeout=2)
            execution_order.append("blocker")

        runner.enqueue(blocker, priority=0)
        self.assertTrue(blocker_started.wait(timeout=1))

        def run_meeting() -> None:
            runner.submit(lambda: execution_order.append("meeting"), priority=100)

        def run_voice() -> None:
            runner.submit(lambda: execution_order.append("voice"), priority=10)

        meeting_thread = threading.Thread(target=run_meeting)
        voice_thread = threading.Thread(target=run_voice)
        meeting_thread.start()
        voice_thread.start()
        time.sleep(0.1)
        release_blocker.set()
        meeting_thread.join(timeout=2)
        voice_thread.join(timeout=2)

        self.assertEqual(execution_order, ["blocker", "voice", "meeting"])

    def test_queue_wait_timeout_cancels_queued_voice_request(self) -> None:
        runner = TaskRunner(name="timeout-test", workers=1)
        release_blocker = threading.Event()
        blocker_started = threading.Event()
        executed: list[str] = []

        def blocker() -> None:
            blocker_started.set()
            release_blocker.wait(timeout=2)
            executed.append("blocker")

        runner.enqueue(blocker, priority=0)
        self.assertTrue(blocker_started.wait(timeout=1))

        with self.assertRaises(QueueWaitTimeoutError):
            runner.submit(
                lambda: executed.append("voice"),
                priority=10,
                wait_timeout_sec=0.1,
            )

        release_blocker.set()
        time.sleep(0.2)
        self.assertEqual(executed, ["blocker"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
