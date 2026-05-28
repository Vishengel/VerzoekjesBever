from dataclasses import dataclass


@dataclass
class QueueItem:
    track_name: str
    artist: str
    album_art_url: str
    requester: str
    track_uri: str

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
