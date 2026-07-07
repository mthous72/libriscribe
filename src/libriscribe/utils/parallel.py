"""Bounded parallel execution (B29).

A small, dependency-free runner for fanning a sync function over many items with a hard cap
on concurrent calls — the shared engine for multi-call LLM work (AI gap scan, Auto-mode
exploration). The cap is per-project (`ProjectKnowledgeBase.max_concurrency`); **1 disables
parallelism entirely** (runs sequentially, no threads) for providers that rate-limit concurrent
requests (e.g. OpenRouter free tier). LM Studio allows 4 concurrent predictions — the default.

`bounded_map` never raises for a failing item: that item's result is ``None`` and the rest keep
going, so one bad call can't sink a whole batch. Results are returned in input order regardless
of completion order.
"""
from __future__ import annotations

import concurrent.futures
import logging
import threading
from typing import Callable, Iterable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")


def clamp_workers(value, default: int = 4) -> int:
    """Coerce a configured concurrency to a usable worker count (>= 1). 1 = serial / off."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = default
    return max(1, n)


def resolve_max_workers(kb, default: int = 4) -> int:
    """The concurrency cap for a project (its `max_concurrency`, clamped to >= 1)."""
    return clamp_workers(getattr(kb, "max_concurrency", default), default)


def bounded_map(
    fn: Callable[[T], R],
    items: Iterable[T],
    max_workers: int,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> list[R | None]:
    """Apply ``fn`` to each item with at most ``max_workers`` running at once.

    - Returns results aligned to input order (not completion order).
    - An item whose ``fn`` raises yields ``None`` (logged); siblings are unaffected.
    - ``max_workers <= 1`` runs sequentially with no thread pool — the "off" switch.
    - ``on_progress(done, total)`` fires after each item finishes (from a worker thread when
      parallel), for live counters.
    """
    items = list(items)
    total = len(items)
    results: list[R | None] = [None] * total
    if total == 0:
        return results

    workers = clamp_workers(max_workers)

    if workers == 1:
        for i, item in enumerate(items):
            try:
                results[i] = fn(item)
            except Exception:  # noqa: BLE001 — isolate per-item failure
                logger.exception("bounded_map item %d failed", i)
            if on_progress:
                on_progress(i + 1, total)
        return results

    done = 0
    lock = threading.Lock()
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(workers, total)) as ex:
        future_to_idx = {ex.submit(fn, item): i for i, item in enumerate(items)}
        for fut in concurrent.futures.as_completed(future_to_idx):
            i = future_to_idx[fut]
            try:
                results[i] = fut.result()
            except Exception:  # noqa: BLE001 — isolate per-item failure
                logger.exception("bounded_map item %d failed", i)
            if on_progress:
                with lock:
                    done += 1
                    d = done
                on_progress(d, total)
    return results
