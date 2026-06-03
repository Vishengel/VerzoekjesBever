"""Central logging configuration for VerzoekjesBever.

Call setup_logging() once, as early as possible, before NiceGUI/uvicorn start.
Uses dictConfig so uvicorn's own logging setup cannot silently disable our
application loggers (disable_existing_loggers=False).
"""

import logging.config
import os

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "level": LOG_LEVEL,
        "handlers": ["console"],
    },
    "loggers": {
        # Quiet down noisy third-party loggers; app loggers inherit root.
        "urllib3": {"level": "WARNING"},
        "spotipy": {"level": "WARNING"},
        "watchfiles": {"level": "WARNING"},
    },
}


def setup_logging() -> None:
    logging.config.dictConfig(LOGGING_CONFIG)
