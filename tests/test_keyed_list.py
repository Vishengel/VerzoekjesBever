import pytest

from keyed_list import Delete, DuplicateKeyError, Insert, Move, diff_keyed


def _apply(old, ops):
    """Reference interpreter: apply ops to a list of keys, return final order.

    Relies on diff_keyed's guarantee that all Delete ops come before any
    Insert/Move ops, so the initial filter is safe to apply up-front.
    """
    cur = [k for k in old if k not in {o.key for o in ops if isinstance(o, Delete)}]
    for op in ops:
        if isinstance(op, Insert):
            cur.insert(op.index, op.key)
        elif isinstance(op, Move):
            cur.remove(op.key)
            cur.insert(op.index, op.key)
    return cur


def test_noop_when_identical():
    pytest.assume(diff_keyed(["a", "b", "c"], ["a", "b", "c"]) == [])


def test_delete_from_front_no_moves():
    ops = diff_keyed(["a", "b", "c"], ["b", "c"])
    pytest.assume(ops == [Delete("a")])
    pytest.assume(_apply(["a", "b", "c"], ops) == ["b", "c"])


def test_insert_at_head():
    ops = diff_keyed(["a", "b"], ["x", "a", "b"])
    pytest.assume(Insert("x", 0) in ops)
    pytest.assume(_apply(["a", "b"], ops) == ["x", "a", "b"])


def test_insert_at_tail():
    ops = diff_keyed(["a", "b"], ["a", "b", "x"])
    pytest.assume(_apply(["a", "b"], ops) == ["a", "b", "x"])


def test_move_to_top():
    ops = diff_keyed(["a", "b", "c"], ["c", "a", "b"])
    pytest.assume(_apply(["a", "b", "c"], ops) == ["c", "a", "b"])
    pytest.assume(sum(isinstance(o, Move) for o in ops) == 1)


def test_swap_adjacent():
    ops = diff_keyed(["a", "b", "c", "d"], ["a", "c", "b", "d"])
    pytest.assume(_apply(["a", "b", "c", "d"], ops) == ["a", "c", "b", "d"])
    pytest.assume(sum(isinstance(o, Move) for o in ops) == 1)


def test_combined_add_remove_reorder():
    old = ["a", "b", "c", "d"]
    new = ["d", "x", "b"]
    ops = diff_keyed(old, new)
    pytest.assume(_apply(old, ops) == new)


def test_empty_to_full():
    ops = diff_keyed([], ["a", "b"])
    pytest.assume(_apply([], ops) == ["a", "b"])


def test_full_to_empty():
    ops = diff_keyed(["a", "b"], [])
    pytest.assume(_apply(["a", "b"], ops) == [])


def test_duplicate_key_raises():
    with pytest.raises(DuplicateKeyError):
        diff_keyed(["a"], ["b", "b"])
