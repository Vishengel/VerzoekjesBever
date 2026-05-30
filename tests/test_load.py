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


@pytest.mark.load
@pytest.mark.parametrize("size", SIZES)
def test_remove_from_middle(tmp_path: Path, size: int):
    store = _filled_store(tmp_path, size)
    middle_uid = store.queue[size // 2].uid

    elapsed, _ = _time_ms(lambda: store.remove_from_queue(middle_uid))

    print(f"remove_from_queue @{size}: {elapsed:.1f}ms")
    pytest.assume(
        elapsed < THRESHOLD_MS, f"Removing from queue of {size} took {elapsed:.1f}ms"
    )
    pytest.assume(len(store.queue) == size - 1)


@pytest.mark.load
@pytest.mark.parametrize("size", SIZES)
def test_move_to_top(tmp_path: Path, size: int):
    store = _filled_store(tmp_path, size)
    last_uid = store.queue[-1].uid

    elapsed, _ = _time_ms(lambda: store.move_to_top(last_uid))

    print(f"move_to_top @{size}: {elapsed:.1f}ms")
    pytest.assume(
        elapsed < THRESHOLD_MS, f"move_to_top in queue of {size} took {elapsed:.1f}ms"
    )
    pytest.assume(store.queue[0].uid == last_uid)


@pytest.mark.load
@pytest.mark.parametrize("size", SIZES)
def test_move_up(tmp_path: Path, size: int):
    store = _filled_store(tmp_path, size)
    last_uid = store.queue[-1].uid

    elapsed, _ = _time_ms(lambda: store.move_up(last_uid))

    print(f"move_up @{size}: {elapsed:.1f}ms")
    pytest.assume(
        elapsed < THRESHOLD_MS, f"move_up in queue of {size} took {elapsed:.1f}ms"
    )
    pytest.assume(store.queue[-2].uid == last_uid)


@pytest.mark.load
@pytest.mark.parametrize("size", SIZES)
def test_move_down(tmp_path: Path, size: int):
    store = _filled_store(tmp_path, size)
    first_uid = store.queue[0].uid

    elapsed, _ = _time_ms(lambda: store.move_down(first_uid))

    print(f"move_down @{size}: {elapsed:.1f}ms")
    pytest.assume(
        elapsed < THRESHOLD_MS, f"move_down in queue of {size} took {elapsed:.1f}ms"
    )
    pytest.assume(store.queue[1].uid == first_uid)


@pytest.mark.load
@pytest.mark.parametrize("size", SIZES)
def test_pop_next(tmp_path: Path, size: int):
    store = _filled_store(tmp_path, size)

    elapsed, item = _time_ms(lambda: store.pop_next())

    print(f"pop_next @{size}: {elapsed:.1f}ms")
    pytest.assume(
        elapsed < THRESHOLD_MS, f"pop_next from queue of {size} took {elapsed:.1f}ms"
    )
    pytest.assume(item is not None)
    pytest.assume(len(store.queue) == size - 1)
