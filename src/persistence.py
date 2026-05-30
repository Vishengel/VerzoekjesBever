import json
import logging
from pathlib import Path

from models import PlaybackState, QueueItem

logger = logging.getLogger(__name__)


class QueueStore:
    def __init__(self, path: Path):
        self._path = path
        self.session_name: str | None = None
        self.device_id: str | None = None
        self.playback_state: PlaybackState = PlaybackState.IDLE
        self.currently_playing: QueueItem | None = None
        self.queue: list[QueueItem] = []
        self._load()

    @property
    def has_session(self) -> bool:
        return self.session_name is not None

    def start_session(self, name: str, device_id: str) -> None:
        self.session_name = name
        self.device_id = device_id
        self.playback_state = PlaybackState.IDLE
        self.currently_playing = None
        self.queue = []
        self._save()

    def add_to_queue(self, item: QueueItem, top: bool = False) -> None:
        if top:
            self.queue.insert(0, item)
        else:
            self.queue.append(item)
        self._save()

    def remove_from_queue(self, track_uri: str) -> None:
        self.queue = [q for q in self.queue if q.track_uri != track_uri]
        self._save()

    def pop_next(self) -> QueueItem | None:
        if not self.queue:
            return None
        item = self.queue.pop(0)
        self._save()
        return item

    def clear_queue(self) -> None:
        self.queue = []
        self._save()

    def move_to_top(self, track_uri: str) -> None:
        item = next((q for q in self.queue if q.track_uri == track_uri), None)
        if item is None:
            return
        self.queue = [item] + [q for q in self.queue if q.track_uri != track_uri]
        self._save()

    def move_up(self, track_uri: str) -> None:
        idx = next(
            (i for i, q in enumerate(self.queue) if q.track_uri == track_uri), None
        )
        if idx is None or idx == 0:
            return
        self.queue[idx], self.queue[idx - 1] = self.queue[idx - 1], self.queue[idx]
        self._save()

    def move_down(self, track_uri: str) -> None:
        idx = next(
            (i for i, q in enumerate(self.queue) if q.track_uri == track_uri), None
        )
        if idx is None or idx == len(self.queue) - 1:
            return
        self.queue[idx], self.queue[idx + 1] = self.queue[idx + 1], self.queue[idx]
        self._save()

    def set_currently_playing(self, item: QueueItem, state: PlaybackState) -> None:
        self.currently_playing = item
        self.playback_state = state
        self._save()

    def clear_currently_playing(self) -> None:
        self.currently_playing = None
        self.playback_state = PlaybackState.IDLE
        self._save()

    def set_playback_state(self, state: PlaybackState) -> None:
        self.playback_state = state
        self._save()

    def update_requester(self, track_uri: str, requester: str) -> None:
        if self.currently_playing and self.currently_playing.track_uri == track_uri:
            self.currently_playing.requester = requester
            self._save()
            return
        for item in self.queue:
            if item.track_uri == track_uri:
                item.requester = requester
                self._save()
                return

    def get_known_requesters(self) -> list[str]:
        names: set[str] = set()
        if self.currently_playing and self.currently_playing.requester:
            names.add(self.currently_playing.requester)
        for item in self.queue:
            if item.requester:
                names.add(item.requester)
        return sorted(names)

    def set_device(self, device_id: str) -> None:
        self.device_id = device_id
        self._save()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
        except (json.JSONDecodeError, ValueError):
            logger.warning("Corrupt session file at %s, starting fresh", self._path)
            return
        self.session_name = data.get("session_name")
        self.device_id = data.get("device_id")
        self.playback_state = PlaybackState(data.get("playback_state", "idle"))
        cp = data.get("currently_playing")
        self.currently_playing = QueueItem.from_dict(cp) if cp else None
        self.queue = [QueueItem.from_dict(q) for q in data.get("queue", [])]

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "session_name": self.session_name,
            "device_id": self.device_id,
            "playback_state": self.playback_state.value,
            "currently_playing": self.currently_playing.to_dict()
            if self.currently_playing
            else None,
            "queue": [q.to_dict() for q in self.queue],
        }
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(self._path)
