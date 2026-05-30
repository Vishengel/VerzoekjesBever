from dataclasses import asdict, dataclass, field
from enum import StrEnum
from uuid import uuid4


class PlaybackState(StrEnum):
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"


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


@dataclass
class QueueItem:
    track_name: str
    artist: str
    album_art_url: str
    requester: str
    track_uri: str
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
        )
