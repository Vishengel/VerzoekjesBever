import time
from pathlib import Path

import pytest

from load_test_utils import make_fake_items
from persistence import QueueStore

SIZES = [10, 50, 100, 500]
THRESHOLD_MS = 100


def _filled_store(tmp_path: Path, size: int) -> QueueStore:
    store = QueueStore(tmp_path / "session.json")
    store.start_session("Benchmark", "dev1")
    for item in make_fake_items(size):
        store.add_to_queue(item)
    return store


def _time_ms(fn) -> float:
    start = time.perf_counter()
    result = fn()
    elapsed = (time.perf_counter() - start) * 1000
    return elapsed, result


@pytest.mark.load
@pytest.mark.parametrize("size", SIZES)
def test_add_n_items(tmp_path: Path, size: int):
    store = QueueStore(tmp_path / "session.json")
    store.start_session("Benchmark", "dev1")
    items = make_fake_items(size)

    elapsed, _ = _time_ms(lambda: [store.add_to_queue(item) for item in items])

    print(f"add_to_queue x{size}: {elapsed:.1f}ms")
    pytest.assume(
        elapsed < THRESHOLD_MS * size / 10, f"Adding {size} items took {elapsed:.1f}ms"
    )
    pytest.assume(len(store.queue) == size)


@pytest.mark.load
@pytest.mark.parametrize("size", SIZES)
def test_get_queue(tmp_path: Path, size: int):
    store = _filled_store(tmp_path, size)

    elapsed, queue = _time_ms(lambda: store.queue)

    print(f"get_queue @{size}: {elapsed:.1f}ms")
    pytest.assume(
        elapsed < THRESHOLD_MS, f"Getting queue of {size} took {elapsed:.1f}ms"
    )
    pytest.assume(len(queue) == size)
