# VerzoekjesBever

Party song request app. A DJ controls playback through Spotify while an audience display shows the current queue.

## Pages

| Route | Purpose                                           |
|-------|---------------------------------------------------|
| `/` | Setup: create or resume a party session           |
| `/dj` | DJ dashboard: manage queue, control playback      |
| `/display` | Audience view: shows current song and queue       |

## Prerequisites

- A [Spotify Developer](https://developer.spotify.com/dashboard) app with Client ID, Client Secret, and Redirect URI
- An active Spotify Premium account (required for playback control)
- **Either** [Docker](https://docs.docker.com/get-docker/) **or** [uv](https://docs.astral.sh/uv/) (uv downloads the right Python version automatically)

## Configuration

Copy the example env file and fill in your Spotify credentials:

```sh
cp .example.env .env
```

```
SPOTIPY_CLIENT_ID=your-client-id
SPOTIPY_CLIENT_SECRET=your-client-secret
```

The redirect URI defaults to `http://127.0.0.1:8000/auth/spotify/callback`. Add the same URI to your Spotify app's Redirect URI settings in the developer dashboard.

## Setup with uv

### Installing uv

[uv](https://docs.astral.sh/uv/) is a fast Python package manager.

```sh
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

```sh
uv sync
uv run python src/main.py
```

The app runs at [http://localhost:8000](http://localhost:8000).

## Setup with Docker

A multi-platform image is published to GHCR on every push to `master`. Docker Compose pulls it by default.

### Run (pre-built image)

```sh
docker compose up
```

### Build locally

```sh
docker compose -f docker-compose.yml -f docker-compose.build.yml up --build
```

### Development (hot reload)

```sh
docker compose -f docker-compose.yml -f docker-compose.build.yml -f docker-compose.dev.yml up --build
```

Source files are bind-mounted. Edits to `src/` trigger automatic reload.

Session state persists in `./data/`, Spotify auth cache in `./cache/`.

## Running tests

```sh
uv sync --group dev
uv run pytest
```
