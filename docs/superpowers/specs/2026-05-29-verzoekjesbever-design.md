# VerzoekjesBever — Design Spec

## Overview

Party song request app. Guests pay (external system, out of scope) to request songs. The DJ uses this app to manage a Spotify playlist: adding songs, prioritizing requests, and removing the currently playing track. An audience-facing beamer display shows the live queue with requester names.

## Constraints

- Runs locally on a single machine
- Single DJ operator
- Payment handling is out of scope
- App manages the playlist only — Spotify app handles playback (no Premium playback API dependency)
- Built with Python + NiceGUI (all-Python stack)

## Architecture

**Layered architecture:** NiceGUI pages → PartyService → SpotifyClient + Persistence

```
NiceGUI (single process)
├── /setup    → Startup page (playlist selection/creation)
├── /dj       → DJ interface
└── /         → Audience beamer display
        │
   PartyService (singleton)
   ├── queue state
   ├── requester map
   ├── currently playing
   └── notify_listeners()
        │
   ├── SpotifyClient (Spotify Web API)
   └── persistence.json (requester → track mapping)
```

- **PartyService** is the single source of truth for app state
- NiceGUI pages only interact with PartyService, never SpotifyClient directly
- Spotify is the source of truth for the playlist itself
- Requester names persisted to local JSON file (survives restart)

## DJ Actions

1. **Search songs** — search by song name or artist via Spotify search API
2. **Add song to queue** — appends to end of Spotify playlist, records requester name
3. **Add song to top** — inserts at position 1 (after currently playing) in Spotify playlist
4. **Remove currently playing** — removes current track from playlist; Spotify advances to next song

## DJ Interface (/dj)

Two-panel layout:

**Left panel — Search & Add:**
- Requester name input field (enter before searching)
- Search bar + search button
- Search results list: album art, song title, artist, "Add" button, "Top" button per result

**Right panel — Current Queue:**
- Currently playing: highlighted with Spotify green border, album art, title, artist, requester name, "Remove" button
- Up next: numbered list with album art thumbnail, title, artist, requester name

**Workflow:** Enter guest name → search song → click Add (bottom) or Top (next up)

## Audience Beamer Display (/)

Compact list layout, designed for projection:

- **Header:** Beaver emoji + "VERZOEKJESBEVER" branding + party subtitle
- **Now playing card:** Large, Spotify-green background, album art, title, artist, requester name
- **Up next list:** Numbered rows with album art thumbnails, title, artist, requester name (right-aligned)
- Dark theme (dark navy/black background), Spotify green accents, orange for requester names

## Startup Flow

1. App starts → Spotify OAuth (cached after first login)
2. DJ sees startup page at `/setup`:
   - "Create new playlist" (auto-named: "VerzoekjesBever — 29 May 2026")
   - "Pick existing playlist" (dropdown of user's playlists)
3. After selection → redirects to `/dj`, audience display at `/` goes live

## Real-Time Updates

- **WebSockets** via NiceGUI's built-in broadcast mechanism
- When DJ modifies queue → PartyService notifies all subscribed audience clients → instant UI update
- **Currently playing detection:** background poller calls Spotify "Get Currently Playing Track" endpoint every 3 seconds, updates state and notifies listeners on change

## PartyService API

```python
class PartyService:
    # Startup
    start_session(playlist_id: str | None)  # None = create new playlist

    # DJ actions
    search_songs(query: str) -> list[QueueItem]
    add_song(track_id: str, requester: str, top: bool = False)
    remove_currently_playing()

    # State
    get_queue() -> list[QueueItem]
    get_currently_playing() -> QueueItem | None

    # Real-time
    subscribe(callback)
    poll_currently_playing()  # called by background timer
```

## Data Model

```python
@dataclass
class QueueItem:
    track_name: str
    artist: str
    album_art_url: str
    requester: str
    track_uri: str
```

## Persistence

- **Playlist state:** lives in Spotify (source of truth)
- **Requester map:** `{track_uri: [requester_name, ...]}` saved to local JSON file, written on every add/remove. List of names because the same song can be requested by multiple guests.
- On restart: queue reloaded from Spotify playlist, requester names reloaded from JSON, currently playing re-detected via poll

## File Structure

```
src/
├── main.py              # NiceGUI app entry, page routing
├── config.py            # Config (existing, extended)
├── spotify_client.py    # Spotify client (existing, extended with search + currently playing)
├── party_service.py     # PartyService — all business logic
├── persistence.py       # JSON read/write for requester map
├── models.py            # QueueItem dataclass
├── pages/
│   ├── dj.py            # DJ interface page
│   ├── audience.py      # Beamer display page
│   └── startup.py       # Playlist selection/creation page
└── util.py              # Existing util
```

## Error Handling

| Scenario | Behavior |
|---|---|
| Spotify token expires | spotipy auto-refreshes via SpotifyOAuth |
| Duplicate song requested | Allowed — show warning but don't block |
| Queue empty | Audience display shows "No songs yet — make a request!" with beaver |
| Remove currently playing (race) | Remove from playlist, poll picks up new track within 3s |
| App crash/restart | Requester map reloads from JSON, queue from Spotify, audience clients auto-reconnect |
| Search returns nothing | Show "No results" in DJ panel |
| Multiple DJ tabs | Works — PartyService is singleton, shared state |

## Technology

- **Python 3.12+**
- **NiceGUI** — web UI framework (serves both DJ and audience pages)
- **spotipy** — Spotify Web API client (existing dependency)
- **pydantic / pydantic-settings** — config management (existing)
