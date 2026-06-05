import json
import logging
from datetime import datetime
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from models import DEFAULT_SHAME_TEMPLATES, PlaybackState, QueueItem, ShameTemplate

logger = logging.getLogger(__name__)


class QueueStore:
    def __init__(self, path: Path):
        self._path = path
        self._session_name: str | None = None
        self._device_id: str | None = None
        self._playback_state: PlaybackState = PlaybackState.IDLE
        self._currently_playing: QueueItem | None = None
        self._queue: list[QueueItem] = []
        self._adem_mode_active: bool = False
        self._party_end_time: datetime | None = None
        self._load()

    @property
    def has_session(self) -> bool:
        return self._session_name is not None

    @property
    def session_name(self) -> str | None:
        return self._session_name

    @property
    def device_id(self) -> str | None:
        return self._device_id

    @property
    def playback_state(self) -> PlaybackState:
        return self._playback_state

    @property
    def currently_playing(self) -> QueueItem | None:
        return self._currently_playing

    @property
    def queue(self) -> list[QueueItem]:
        return list(self._queue)

    @property
    def adem_mode_active(self) -> bool:
        return self._adem_mode_active

    @property
    def party_end_time(self) -> datetime | None:
        return self._party_end_time

    def set_party_end_time(self, end_time: datetime | None) -> None:
        self._party_end_time = end_time
        self._save()

    def start_session(self, name: str, device_id: str) -> None:
        self._session_name = name
        self._device_id = device_id
        self._playback_state = PlaybackState.IDLE
        self._currently_playing = None
        self._queue = []
        self._adem_mode_active = False
        self._save()

    def add_to_queue(self, item: QueueItem, top: bool = False) -> None:
        item = replace(item, uid=uuid4().hex[:8])
        if top:
            self._queue.insert(0, item)
        else:
            self._queue.append(item)
        self._save()

    def remove_from_queue(self, uid: str) -> None:
        self._queue = [q for q in self._queue if q.uid != uid]
        self._save()

    def pop_next(self) -> QueueItem | None:
        if not self._queue:
            return None
        item = self._queue.pop(0)
        self._save()
        return item

    def clear_queue(self) -> None:
        self._queue = []
        self._save()

    def move_to_top(self, uid: str) -> None:
        item = next((q for q in self._queue if q.uid == uid), None)
        if item is None:
            return
        self._queue = [item] + [q for q in self._queue if q.uid != uid]
        self._save()

    def move_up(self, uid: str) -> None:
        idx = next((i for i, q in enumerate(self._queue) if q.uid == uid), None)
        if idx is None or idx == 0:
            return
        self._queue[idx], self._queue[idx - 1] = self._queue[idx - 1], self._queue[idx]
        self._save()

    def move_down(self, uid: str) -> None:
        idx = next((i for i, q in enumerate(self._queue) if q.uid == uid), None)
        if idx is None or idx == len(self._queue) - 1:
            return
        self._queue[idx], self._queue[idx + 1] = self._queue[idx + 1], self._queue[idx]
        self._save()

    def set_currently_playing(self, item: QueueItem, state: PlaybackState) -> None:
        self._currently_playing = item
        self._playback_state = state
        self._save()

    def clear_currently_playing(self) -> None:
        self._currently_playing = None
        self._playback_state = PlaybackState.IDLE
        self._save()

    def set_playback_state(self, state: PlaybackState) -> None:
        self._playback_state = state
        self._save()

    def update_requester(self, uid: str, requester: str) -> None:
        if self._currently_playing and self._currently_playing.uid == uid:
            self._currently_playing = replace(
                self._currently_playing, requester=requester
            )
            self._save()
            return
        self._queue = [
            replace(item, requester=requester) if item.uid == uid else item
            for item in self._queue
        ]
        self._save()

    def get_known_requesters(self) -> list[str]:
        names: set[str] = set()
        if self._currently_playing and self._currently_playing.requester:
            names.add(self._currently_playing.requester)
        for item in self._queue:
            if item.requester:
                names.add(item.requester)
        return sorted(names)

    def set_adem_mode_active(self, active: bool) -> None:
        self._adem_mode_active = active
        self._save()

    def set_device(self, device_id: str) -> None:
        self._device_id = device_id
        self._save()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
        except (json.JSONDecodeError, ValueError):
            logger.warning("Corrupt session file at %s, starting fresh", self._path)
            return
        self._session_name = data.get("session_name")
        self._device_id = data.get("device_id")
        self._playback_state = PlaybackState(data.get("playback_state", "idle"))
        cp = data.get("currently_playing")
        self._currently_playing = QueueItem.from_dict(cp) if cp else None
        self._queue = [QueueItem.from_dict(q) for q in data.get("queue", [])]
        self._adem_mode_active = data.get(
            "adem_mode_active", data.get("demo_queue_active", False)
        )
        pet = data.get("party_end_time")
        try:
            self._party_end_time = datetime.fromisoformat(pet) if pet else None
        except ValueError:
            logger.warning("Invalid party_end_time in %s, ignoring", self._path)
            self._party_end_time = None

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "session_name": self._session_name,
            "device_id": self._device_id,
            "playback_state": self._playback_state.value,
            "currently_playing": self._currently_playing.to_dict()
            if self._currently_playing
            else None,
            "queue": [q.to_dict() for q in self._queue],
            "adem_mode_active": self._adem_mode_active,
            "party_end_time": self._party_end_time.isoformat()
            if self._party_end_time
            else None,
        }
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(self._path)


class ShameTemplateStore:
    """Persists shame-message templates independently of the party session so
    they outlive session resets. Seeds with defaults on first run."""

    def __init__(self, path: Path):
        self._path = path
        self._templates: list[ShameTemplate] = []
        self._load()

    def get_all(self) -> list[ShameTemplate]:
        return list(self._templates)

    def add(self, text: str) -> None:
        self._templates.append(ShameTemplate(text=text))
        self._save()

    def remove(self, uid: str) -> None:
        self._templates = [t for t in self._templates if t.uid != uid]
        self._save()

    def reset_to_default(self) -> None:
        self._templates = [ShameTemplate(text=t) for t in DEFAULT_SHAME_TEMPLATES]
        self._save()

    def _load(self) -> None:
        if not self._path.exists():
            # First run: seed defaults and persist so the file exists.
            self.reset_to_default()
            return
        try:
            data = json.loads(self._path.read_text())
        except (json.JSONDecodeError, ValueError):
            logger.warning(
                "Corrupt shame-templates file at %s, restoring defaults", self._path
            )
            self.reset_to_default()
            return
        self._templates = [
            ShameTemplate.from_dict(t) for t in data.get("templates", [])
        ]

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {"templates": [t.to_dict() for t in self._templates]}
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(self._path)
