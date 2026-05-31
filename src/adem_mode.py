from __future__ import annotations

from typing import TYPE_CHECKING

from models import QueueItem

if TYPE_CHECKING:
    from persistence import QueueStore

ADEMNOOD_ITEM = QueueItem(
    track_name="Ademnood",
    artist="Linda Roos & Jessica",
    album_art_url="https://i.scdn.co/image/ab67616d0000b273eadf932fba8bf38eba3947a1",
    track_uri="spotify:track:5ljuGR6Fv7B2mviKflDoE4",
    requester="🦫",
)
ADEM_MODE_QUEUE_SIZE = 50


class AdemMode:
    def __init__(self, store: QueueStore):
        self._store = store

    @property
    def active(self) -> bool:
        return self._store.adem_mode_active

    def activate(self) -> None:
        for _ in range(ADEM_MODE_QUEUE_SIZE):
            self._store.add_to_queue(ADEMNOOD_ITEM)
        self._store.set_adem_mode_active(True)

    def on_user_add(self) -> None:
        if not self.active:
            return
        if any(
            q.track_uri == ADEMNOOD_ITEM.track_uri
            and q.requester == ADEMNOOD_ITEM.requester
            for q in self._store.queue
        ):
            self._store.clear_queue()

    def refill_if_needed(self) -> bool:
        if self.active and not self._store.queue:
            self.activate()
            return True
        return False
