from models import QueueItem

FAKE_ARTISTS = [
    "DJ Test",
    "Benchmark Band",
    "Load Runner",
    "Stress Test",
    "Queue Filler",
]
FAKE_REQUESTERS = ["Alice", "Bob", "Charlie", "Dana", "Eve"]


def make_fake_items(n: int) -> list[QueueItem]:
    return [
        QueueItem(
            track_name=f"Load Test Track {i + 1}",
            artist=FAKE_ARTISTS[i % len(FAKE_ARTISTS)],
            album_art_url=f"https://placehold.co/300x300?text=Track+{i + 1}",
            requester=FAKE_REQUESTERS[i % len(FAKE_REQUESTERS)],
            track_uri=f"spotify:track:loadtest_{i}",
        )
        for i in range(n)
    ]
