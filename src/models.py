from dataclasses import dataclass
from enum import StrEnum


class PlaybackState(StrEnum):
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"


@dataclass
class QueueItem:
    track_name: str
    artist: str
    album_art_url: str
    requester: str
    track_uri: str

    def to_dict(self) -> dict:
        return {
            "track_name": self.track_name,
            "artist": self.artist,
            "album_art_url": self.album_art_url,
            "track_uri": self.track_uri,
            "requester": self.requester,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QueueItem":
        return cls(
            track_name=data["track_name"],
            artist=data["artist"],
            album_art_url=data["album_art_url"],
            track_uri=data["track_uri"],
            requester=data["requester"],
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
