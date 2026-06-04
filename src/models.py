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


def select_album_art(images: list[dict]) -> tuple[str, str]:
    """Pick (full_url, thumb_url) from a Spotify album images array.

    Spotify returns several sizes (typically 640/300/64px) ordered widest-first,
    each with an optional ``width``. ``full`` is the smallest image at least
    200px wide (≈300px) — enough for the now-playing card without shipping the
    640px original to every client. ``thumb`` is the smallest image (≈64px) for
    the tiny queue-row covers. Falls back to the largest image when nothing
    meets the threshold or widths are missing; ``[]`` yields ``("", "")``.
    """
    if not images:
        return "", ""

    def width(img: dict) -> int:
        return img.get("width") or 0

    ordered = sorted(images, key=width)  # ascending; stable for equal/missing
    thumb = ordered[0]["url"]
    full = next(
        (img["url"] for img in ordered if width(img) >= 200),
        ordered[-1]["url"],
    )
    return full, thumb


@dataclass(frozen=True)
class QueueItem:
    track_name: str
    artist: str
    album_art_url: str
    requester: str
    track_uri: str
    thumb_url: str = ""
    duration_ms: int = 0
    uid: str = field(default_factory=lambda: uuid4().hex[:8])

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "QueueItem":
        full = data["album_art_url"]
        return cls(
            track_name=data["track_name"],
            artist=data["artist"],
            album_art_url=full,
            track_uri=data["track_uri"],
            requester=data["requester"],
            thumb_url=data.get("thumb_url") or full,
            duration_ms=data.get("duration_ms", 0),
            uid=data.get("uid", uuid4().hex[:8]),
        )

    @classmethod
    def from_spotify_track(cls, track: dict, requester: str) -> "QueueItem":
        full, thumb = select_album_art(track["album"]["images"])
        return cls(
            track_name=track["name"],
            artist=track["artists"][0]["name"],
            album_art_url=full,
            thumb_url=thumb,
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


def _matches(item: QueueItem, needle: str) -> bool:
    """Case-insensitive substring test over an item's track, artist, requester."""
    return needle in f"{item.track_name} {item.artist} {item.requester or ''}".lower()


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

    results: list[QueueMatch] = []
    if current is not None and _matches(current, needle):
        results.append(QueueMatch(item=current, position=0, eta_ms=0, now_playing=True))

    eta_ms = 0
    for index, item in enumerate(queue):
        if _matches(item, needle):
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


@dataclass(frozen=True)
class PositionedItem:
    item: QueueItem
    position: int  # 1-based position in the full queue
    eta_ms: int  # ms until it plays (sum of durations ahead; current treated as done)


def filter_queue_with_positions(
    queue: list[QueueItem],
    term: str,
) -> list[PositionedItem]:
    """Filter the queue by a free-text term, keeping each match's real position.

    Case-insensitive substring over track_name + artist + requester. Each result
    carries its 1-based position in the *full* queue and a rough ETA (sum of
    durations of the songs ahead of it), so a filtered view can show the actual
    position and wait time regardless of which items are hidden. An empty or
    whitespace-only term returns every item.
    """
    needle = term.strip().lower()
    positioned: list[PositionedItem] = []
    eta_ms = 0
    for index, item in enumerate(queue):
        positioned.append(PositionedItem(item=item, position=index + 1, eta_ms=eta_ms))
        eta_ms += item.duration_ms
    if not needle:
        return positioned
    return [p for p in positioned if _matches(p.item, needle)]


def format_queue_duration(total_ms: int) -> str:
    total_seconds = total_ms // 1000
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m {seconds}s"


def queue_render_signature(
    current: QueueItem | None,
    visible: list[QueueItem],
    *extra: object,
) -> tuple:
    """Cheap equality key for what a queue view currently renders.

    Two renders look identical when the now-playing track (and its editable
    requester), the ordered visible rows (each uid + requester), and any extra
    state passed by the caller (playback state, total song count, etc.) all
    match. Comparing this signature across version bumps lets a client skip the
    full DOM rebuild when a bump did not change anything it actually shows.

    Only fields that can change for a stable uid (the requester) are included
    per row; track/artist/art are immutable for a given uid, and row order is
    captured by the tuple order, so position numbers and ETAs are implied.
    """
    head = (current.uid, current.requester) if current else None
    rows = tuple((item.uid, item.requester) for item in visible)
    return (head, rows, extra)


def format_queue_stats(queue: list[QueueItem]) -> str:
    """One-line queue summary: song count plus total remaining time when known."""
    total_ms = sum(item.duration_ms for item in queue)
    stats = f"⏱ {len(queue)} songs"
    if total_ms:
        stats += f" · {format_queue_duration(total_ms)} remaining"
    return stats
