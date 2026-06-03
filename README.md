# VerzoekjesBever

Party song request app. A DJ controls playback through Spotify while an audience display shows the current queue.

## Pages

| Route | Purpose                                           |
|-------|---------------------------------------------------|
| `/` | Setup: create or resume a party session           |
| `/dj` | DJ dashboard: manage queue, control playback      |
| `/display` | Audience view: shows current song and queue       |

## Prerequisites

### Network

- The machine running VerzoekjesBever and the Spotify playback device (laptop, phone) must be on the **same local network**

### Software & Accounts

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
DJ_PASSWORD=your-dj-password
```

Set `DJ_PASSWORD` to protect the DJ dashboard and setup page behind a login. Leave it empty to disable authentication (anyone with the URL can control playback).

The `/display` route is always public so party guests can view the queue on their phones.

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
`uv run python src/main.py`
```

The app runs at [http://localhost:8000](http://localhost:8000).

## Setup with Docker

A multi-platform image is published to GHCR on every push to `master`.

### Quick start (no clone needed)

Create a project folder with the required config and directories:

```sh
mkdir verzoekjesbever
cd verzoekjesbever
mkdir data cache
```

Create a file called `.env` with your Spotify credentials:

```
SPOTIPY_CLIENT_ID=your-client-id
SPOTIPY_CLIENT_SECRET=your-client-secret
DJ_PASSWORD=your-dj-password
```

Run the container:

```sh
docker run -d -p 8000:8000 --env-file .env -v ./data:/app/data -v ./cache:/app/cache --restart unless-stopped --name verzoekjesbever ghcr.io/vishengel/verzoekjesbever:latest
```

### Run with Docker Compose (pre-built image)

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

## Benchmarking

Navigate to `/benchmark` to load-test the queue with fake tracks. Pick a queue size (10 to 500 items), fill the queue, then open the DJ or audience page to check rendering performance. Requires an active session and DJ authentication.
