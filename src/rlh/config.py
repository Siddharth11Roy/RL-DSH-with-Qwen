"""Loads rlh settings from YAML.

configs/default.yaml is always read first; an optional override file is
deep-merged on top, so a user config only needs the keys it changes.
Missing top-level sections raise early instead of failing mid-training.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "configs" / "default.yaml"
REQUIRED_SECTIONS = ("model", "lora", "harness", "grpo", "world", "endpoint")


class ConfigError(ValueError):
    pass


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"config file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"config must be a mapping: {path}")
    return data


def load_config(override: Path | None = None) -> dict[str, Any]:
    config = _read(DEFAULT_CONFIG)
    if override is not None:
        config = deep_merge(config, _read(override))
    missing = [s for s in REQUIRED_SECTIONS if s not in config]
    if missing:
        raise ConfigError(f"config is missing sections: {', '.join(missing)}")
    return config
