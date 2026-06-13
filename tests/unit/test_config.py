"""Config tests — UT-CFG-01..06."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.common.config import PipelineConfig, load_config
from src.common.errors import ConfigError


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_load_valid_config(mini_cfg):  # UT-CFG-01
    assert isinstance(mini_cfg, PipelineConfig)
    assert mini_cfg.version == "0.1.0"
    assert mini_cfg.sensor.datasets[0].name == "demo"
    # defaults applied where omitted
    assert mini_cfg.assemble.split.fractions["train"] == 0.7


def test_relative_paths_resolved(mini_cfg, workspace):  # UT-CFG-02
    assert Path(mini_cfg.paths.sensor_index).is_absolute()
    assert Path(mini_cfg.paths.data_processed).is_absolute()
    assert str(workspace) in mini_cfg.paths.sensor_index


def test_missing_required_key(workspace):  # UT-CFG-03
    cfg_path = _write(workspace / "config" / "bad.yaml",
                      "version: 0.1.0\npaths: {}\n")  # no sensor
    with pytest.raises(ConfigError) as exc:
        load_config(cfg_path)
    assert "sensor" in str(exc.value)


def test_bad_type(workspace):  # UT-CFG-04
    text = (workspace / "config" / "dataset.yaml").read_text()
    text = text.replace("pre_event_s: 3.0", "pre_event_s: sixty")
    cfg_path = _write(workspace / "config" / "badtype.yaml", text)
    with pytest.raises(ConfigError) as exc:
        load_config(cfg_path)
    assert "pre_event_s" in str(exc.value)


def test_out_of_range_threshold(workspace):  # UT-CFG-05
    text = (workspace / "config" / "dataset.yaml").read_text()
    text = text.replace("min_plausible_hz: 100", "min_plausible_hz: -5")
    cfg_path = _write(workspace / "config" / "badrange.yaml", text)
    with pytest.raises(ConfigError) as exc:
        load_config(cfg_path)
    assert "min_plausible_hz" in str(exc.value)


def test_unsupported_version(workspace):  # UT-CFG-06
    text = (workspace / "config" / "dataset.yaml").read_text()
    text = text.replace("version: 0.1.0", "version: 99.0")
    cfg_path = _write(workspace / "config" / "badver.yaml", text)
    with pytest.raises(ConfigError) as exc:
        load_config(cfg_path)
    assert "version" in str(exc.value).lower()
