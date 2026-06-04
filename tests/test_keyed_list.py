from dataclasses import dataclass, field

import pytest

from keyed_list import Delete, DuplicateKeyError, Insert, KeyedList, Move, diff_keyed


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


class FakeElement:
    """Stand-in for a NiceGUI element: records move/delete, no DOM."""

    def __init__(self, registry: list):
        self._registry = registry
        self.deleted = False
        registry.append(self)

    def move(self, target_container=None, target_index: int = -1) -> "FakeElement":
        self._registry.remove(self)
        self._registry.insert(target_index, self)
        return self

    def delete(self) -> None:
        self.deleted = True
        if self in self._registry:
            self._registry.remove(self)


class FakeContainer:
    """Context manager standing in for a NiceGUI container element."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@dataclass
class VM:
    uid: str
    label: str = ""


@dataclass
class Handle:
    root: FakeElement
    patched: list = field(default_factory=list)


def _make_list():
    registry: list = []
    built: list = []

    def build(vm: VM) -> Handle:
        h = Handle(root=FakeElement(registry))
        built.append(vm.uid)
        return h

    def patch(h: Handle, vm: VM) -> None:
        h.patched.append(vm.label)

    kl = KeyedList(FakeContainer(), key=lambda vm: vm.uid, build=build, patch=patch)
    return kl, registry, built


def test_keyedlist_builds_then_reorders_and_deletes():
    kl, registry, built = _make_list()
    kl.reconcile([VM("a"), VM("b"), VM("c")])
    pytest.assume(built == ["a", "b", "c"])
    pytest.assume(kl.order == ["a", "b", "c"])

    kl.reconcile([VM("c"), VM("a")])  # delete b, move c to front
    pytest.assume("b" not in kl.order)
    pytest.assume(kl.order == ["c", "a"])
    pytest.assume(built == ["a", "b", "c"])  # no rebuilds of survivors


def test_keyedlist_patches_every_current_row_each_reconcile():
    kl, registry, built = _make_list()
    kl.reconcile([VM("a", "1"), VM("b", "2")])
    kl.reconcile([VM("a", "9"), VM("b", "8")])
    pytest.assume(kl.handle("a").patched == ["1", "9"])
    pytest.assume(kl.handle("b").patched == ["2", "8"])


def test_keyedlist_insert_lands_at_correct_index():
    kl, registry, built = _make_list()
    kl.reconcile([VM("a"), VM("c")])
    kl.reconcile([VM("a"), VM("b"), VM("c")])  # insert b between a and c
    pytest.assume(kl.order == ["a", "b", "c"])
    pytest.assume(registry.index(kl.handle("b").root) == 1)
    pytest.assume([h for h in registry] == [kl.handle(k).root for k in ["a", "b", "c"]])
