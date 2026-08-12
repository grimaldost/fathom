"""Run configuration for a tinyetl batch."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_BATCH_SIZE = 500

KNOWN_REGIONS = ("north", "south", "east", "west")


class ConfigError(ValueError):
    """Raised when a configuration file cannot be turned into a Config."""


@dataclass(frozen=True)
class Config:
    """Everything one batch run needs to know."""

    source_uri: str
    dest_path: str
    batch_size: int = DEFAULT_BATCH_SIZE

    def validate(self) -> None:
        if not self.source_uri:
            raise ConfigError("source_uri is required")
        if not self.dest_path:
            raise ConfigError("dest_path is required")
        if self.batch_size <= 0:
            raise ConfigError("batch_size must be positive")


def load_config(path: str | Path) -> Config:
    """Read a JSON config file and return a validated Config."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    config = Config(
        source_uri=raw.get("source_uri", ""),
        dest_path=raw.get("dest_path", ""),
        batch_size=int(raw.get("batch_size", DEFAULT_BATCH_SIZE)),
    )
    config.validate()
    return config
