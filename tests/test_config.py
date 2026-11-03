"""Tests for rlh.config.

Covers loading the shipped defaults, deep-merging an override file on top,
and the errors raised for a missing file or an incomplete config. Uses pytest's
tmp_path so no test touches the real configs/ folder.
"""

from pathlib import Path

import pytest

from rlh.config import ConfigError, deep_merge, load_config


def test_defaults_fit_small_gpu():
    config = load_config()
    assert config["model"]["base"] == "Qwen/Qwen3-1.7B"
    assert config["model"]["load_in_4bit"] is True
    assert config["grpo"]["group_size"] <= 4


def test_override_changes_only_given_keys(tmp_path: Path):
    override = tmp_path / "small.yaml"
    override.write_text("grpo:\n  group_size: 2\n", encoding="utf-8")
    config = load_config(override)
    assert config["grpo"]["group_size"] == 2
    assert config["grpo"]["kl_beta"] == 0.04


def test_deep_merge_keeps_nested_siblings():
    merged = deep_merge({"a": {"x": 1, "y": 2}}, {"a": {"y": 3}})
    assert merged == {"a": {"x": 1, "y": 3}}


def test_missing_file_raises(tmp_path: Path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "nope.yaml")


def test_non_mapping_raises(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("- just\n- a list\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="mapping"):
        load_config(bad)
