import json
from pathlib import Path


class RequesterMap:
    def __init__(self, path: Path):
        self._path = path
        self._data: dict[str, list[str]] = {}
        self._load()

    def add(self, track_uri: str, requester: str) -> None:
        self._data.setdefault(track_uri, []).append(requester)
        self._save()

    def get(self, track_uri: str) -> list[str]:
        return list(self._data.get(track_uri, []))

    def remove(self, track_uri: str) -> None:
        self._data.pop(track_uri, None)
        self._save()

    def _load(self) -> None:
        if self._path.exists():
            self._data = json.loads(self._path.read_text())

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2))
