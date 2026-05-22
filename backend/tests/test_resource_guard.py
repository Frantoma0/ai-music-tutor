from __future__ import annotations

import threading
import time

from app.pipeline.resource_guard import gpu_sequential_guard


def test_gpu_sequential_guard_serializes_threads():
    events: list[tuple[str, float, float]] = []
    lock = threading.Lock()

    def worker(name: str) -> None:
        with gpu_sequential_guard(name):
            start = time.monotonic()
            time.sleep(0.05)
            end = time.monotonic()

        with lock:
            events.append((name, start, end))

    thread_a = threading.Thread(target=worker, args=("a",))
    thread_b = threading.Thread(target=worker, args=("b",))

    started = time.monotonic()

    thread_a.start()
    thread_b.start()

    thread_a.join()
    thread_b.join()

    elapsed = time.monotonic() - started

    assert len(events) == 2

    # If both ran in parallel, elapsed would be close to 0.05s.
    # Sequential execution should be close to 0.10s.
    assert elapsed >= 0.09

    first, second = sorted(events, key=lambda item: item[1])

    assert first[2] <= second[1]
