from __future__ import annotations

from dataclasses import dataclass


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
