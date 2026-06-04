from dataclasses import asdict, dataclass, field
from enum import StrEnum
from uuid import uuid4


class PlaybackState(StrEnum):
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"


class PlaybackSignal(StrEnum):
    NOTHING = "nothing"
    TRACK_ENDED = "track_ended"
    TRACK_LOST = "track_lost"
    EXTERNAL_PAUSE = "external_pause"
    EXTERNAL_RESUME = "external_resume"


class PartyEventType(StrEnum):
    ADDED = "added"
    SKIPPED = "skipped"
    MOVED_TO_TOP = "moved_to_top"


@dataclass(frozen=True)
class PartyEvent:
    kind: PartyEventType
    track_uri: str
    version: int
    is_priority: bool = False


@dataclass(frozen=True)
class PlaybackInfo:
    is_playing: bool
    progress_ms: int
    duration_ms: int
    track_uri: str | None = None


@dataclass(frozen=True)
class QueueItem:
    track_name: str
    artist: str
    album_art_url: str
    requester: str
    track_uri: str
    duration_ms: int = 0
    uid: str = field(default_factory=lambda: uuid4().hex[:8])

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "QueueItem":
        return cls(
            track_name=data["track_name"],
            artist=data["artist"],
            album_art_url=data["album_art_url"],
            track_uri=data["track_uri"],
            requester=data["requester"],
            duration_ms=data.get("duration_ms", 0),
            uid=data.get("uid", uuid4().hex[:8]),
        )

    @classmethod
    def from_spotify_track(cls, track: dict, requester: str) -> "QueueItem":
        images = track["album"]["images"]
        return cls(
            track_name=track["name"],
            artist=track["artists"][0]["name"],
            album_art_url=images[0]["url"] if images else "",
            requester=requester,
            track_uri=track["uri"],
            duration_ms=track.get("duration_ms", 0),
        )


@dataclass(frozen=True)
class QueueMatch:
    item: QueueItem
    position: int  # 1-based queue position; 0 when now_playing
    eta_ms: int  # ms until it plays; 0 when now_playing
    now_playing: bool


def search_queue(
    queue: list[QueueItem],
    current: QueueItem | None,
    query: str,
) -> list[QueueMatch]:
    """Find songs matching a free-text query, with queue position and rough ETA.

    Case-insensitive substring over track_name + artist + requester. ETA for the
    item at index i is the sum of duration_ms of the items ahead of it
    (queue[0:i]); the currently-playing song is treated as ~done and not counted.
    A matching current song yields now_playing=True, position=0, eta_ms=0.
    An empty or whitespace-only query returns no matches.
    """
    needle = query.strip().lower()
    if not needle:
        return []

    def matches(item: QueueItem) -> bool:
        haystack = f"{item.track_name} {item.artist} {item.requester or ''}".lower()
        return needle in haystack

    results: list[QueueMatch] = []
    if current is not None and matches(current):
        results.append(QueueMatch(item=current, position=0, eta_ms=0, now_playing=True))

    eta_ms = 0
    for index, item in enumerate(queue):
        if matches(item):
            results.append(
                QueueMatch(
                    item=item,
                    position=index + 1,
                    eta_ms=eta_ms,
                    now_playing=False,
                )
            )
        eta_ms += item.duration_ms
    return results


def format_queue_duration(total_ms: int) -> str:
    total_seconds = total_ms // 1000
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m {seconds}s"
