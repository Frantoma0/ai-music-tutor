from __future__ import annotations

import threading
from contextlib import contextmanager
from dataclasses import dataclass
from time import monotonic
from typing import Iterator


_GPU_LOCK = threading.Lock()


@dataclass(frozen=True)
class GuardEvent:
    name: str
    wait_seconds: float


@contextmanager
def gpu_sequential_guard(name: str = "gpu_task") -> Iterator[GuardEvent]:
    """
    Process-local sequential guard for GPU-heavy pipeline sections.

    This prevents concurrent Demucs / Basic Pitch execution inside the same
    backend process. It is intentionally small and dependency-free.

    Note:
        This does not coordinate across multiple backend worker processes.
        The current Docker/dev backend runs as a single process, so this is
        enough for the present pipeline hardening requirement.
    """
    started_waiting = monotonic()

    with _GPU_LOCK:
        wait_seconds = monotonic() - started_waiting
        yield GuardEvent(name=name, wait_seconds=round(wait_seconds, 6))
