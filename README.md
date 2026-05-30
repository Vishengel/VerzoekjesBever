# VerzoekjesBever

Party song request app. A DJ controls playback through Spotify while an audience display shows the current queue.

## Pages

| Route | Purpose                                           |
|-------|---------------------------------------------------|
| `/` | Setup: create or resume a party session           |
| `/dj` | DJ dashboard: manage queue, control playback      |
| `/display` | Audience view: shows current song and queue       |

## Prerequisites

- Python 3.12+
- A [Spotify Developer](https://developer.spotify.com/dashboard) app with Client ID, Client Secret, and Redirect URI
- An active Spotify Premium account (required for playback control)

## Configuration

Copy the example env file and fill in your Spotify credentials:

```sh
cp .example.env .env
```

```
SPOTIPY_CLIENT_ID=your-client-id
SPOTIPY_CLIENT_SECRET=your-client-secret
SPOTIPY_REDIRECT_URI=http://localhost:8000/callback
```

## Setup with uv

```sh
uv sync
uv run python src/main.py
```

The app runs at [http://localhost:8000](http://localhost:8000).

## Setup with Docker

### Production

```sh
docker compose up --build
```

Session state persists in `./data/` and Spotify auth cache in `./cache/`.

### Development (hot reload)

```sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Source files are bind-mounted. Edits to `src/` trigger automatic reload.

## Running tests

```sh
uv sync --group dev
uv run pytest
```
