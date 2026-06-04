from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar, runtime_checkable


class DuplicateKeyError(ValueError):
    """Raised when reconcile receives two items sharing a key.

    The keyed reconciler relies on keys being unique per row; a duplicate
    would corrupt the element/handle map, so we fail loudly instead.
    """


@dataclass(frozen=True)
class Insert:
    key: str
    index: int


@dataclass(frozen=True)
class Move:
    key: str
    index: int


@dataclass(frozen=True)
class Delete:
    key: str


Op = Insert | Move | Delete


def diff_keyed(old_keys: list[str], new_keys: list[str]) -> list[Op]:
    """Minimal ops to turn ``old_keys`` (current order) into ``new_keys``.

    Returns ``Delete`` ops first (keys gone from the new list), then walks the
    desired order left-to-right emitting ``Insert`` for new keys and ``Move``
    for surviving keys whose position changed. Applying the ops in order to a
    list mirroring the DOM children yields ``new_keys``. Surviving keys already
    in the correct relative order emit no ``Move`` (so a track advance or a
    requester edit produces zero structural ops). Raises ``DuplicateKeyError``
    if ``new_keys`` contains a duplicate. ``old_keys`` is assumed already-unique
    (it comes from the previous render); only ``new_keys`` is validated.
    """
    seen: set[str] = set()
    for key in new_keys:
        if key in seen:
            raise DuplicateKeyError(f"duplicate key in reconcile: {key!r}")
        seen.add(key)

    ops: list[Op] = []
    ops.extend(Delete(key) for key in old_keys if key not in seen)

    current = [key for key in old_keys if key in seen]
    current_set = set(current)
    for target_index, key in enumerate(new_keys):
        if key not in current_set:
            ops.append(Insert(key, target_index))
            current.insert(target_index, key)
            current_set.add(key)
            continue
        cur_index = current.index(key)
        if cur_index != target_index:
            ops.append(Move(key, target_index))
            current.pop(cur_index)
            current.insert(target_index, key)
    return ops


@runtime_checkable
class RowHandle(Protocol):
    root: object  # the row's outermost element; needs .move() and .delete()


T = TypeVar("T")
H = TypeVar("H", bound=RowHandle)


class KeyedList(Generic[T, H]):
    """Reconcile a container's child rows against an ordered list of view-models.

    ``key`` extracts a stable unique key per view-model. ``build`` creates a row
    once (parented into ``container``) and returns a handle exposing ``.root``;
    ``patch`` updates the mutable fields of an existing row in place. On each
    ``reconcile`` only the diff is applied — new rows built, gone rows deleted,
    reordered rows moved — and every surviving/new row is patched.
    """

    def __init__(
        self,
        container,
        *,
        key: Callable[[T], str],
        build: Callable[[T], H],
        patch: Callable[[H, T], None],
    ) -> None:
        self._container = container
        self._key = key
        self._build = build
        self._patch = patch
        self._handles: dict[str, H] = {}
        self._order: list[str] = []

    @property
    def order(self) -> list[str]:
        return list(self._order)

    def handle(self, key: str) -> H:
        return self._handles[key]

    def reconcile(self, items: list[T]) -> None:
        new_keys = [self._key(item) for item in items]
        ops = diff_keyed(self._order, new_keys)
        item_by_key = dict(zip(new_keys, items, strict=True))
        for op in ops:
            if isinstance(op, Delete):
                self._handles.pop(op.key).root.delete()
            elif isinstance(op, Insert):
                with self._container:
                    handle = self._build(item_by_key[op.key])
                self._handles[op.key] = handle
                handle.root.move(target_index=op.index)
            elif isinstance(op, Move):
                self._handles[op.key].root.move(target_index=op.index)
        self._order = new_keys
        for key, item in item_by_key.items():
            self._patch(self._handles[key], item)
