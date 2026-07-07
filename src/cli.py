"""Stage 5 — CLI & orchestration.

    python -m src.cli sensor   --config config/dataset.yaml [--limit N] [--dry-run]
    python -m src.cli text     ...
    python -m src.cli video    ...
    python -m src.cli assemble ...
    python -m src.cli all      ...
    python -m src.cli evaluate --tier mvp|extended

Each command loads config, builds the stage, runs it, prints the RunSummary, and
exits non-zero on failure (e.g. a missing upstream index).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from .common.config import load_config
from .common.errors import AssemblyError, ConfigError, PipelineError
from .etl.assemble_incidents import IncidentAssembler
from .etl.sensor_etl import SensorETL
from .etl.text_etl import TextETL
from .etl.video_etl import VideoETL
from .evaluate import evaluate_build

app = typer.Typer(add_completion=False, help="Recipe A multimodal CNC dataset pipeline.")

_DEFAULT_CONFIG = "config/dataset.yaml"
ConfigOpt = typer.Option(_DEFAULT_CONFIG, "--config", "-c", help="Path to dataset.yaml")
LimitOpt = typer.Option(None, "--limit", "-n", help="Process at most N units")
DryRunOpt = typer.Option(False, "--dry-run", help="Validate without writing outputs")


def _load(config: str):
    try:
        return load_config(config)
    except ConfigError as exc:
        typer.secho(f"Config error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2)


def _run_stage(stage, limit, dry_run) -> int:
    summ = stage.run(limit=limit, dry_run=dry_run)
    typer.secho(str(summ), fg=typer.colors.GREEN if summ.ok else typer.colors.YELLOW)
    return 0 if summ.ok else 1


@app.command()
def sensor(config: str = ConfigOpt, limit: Optional[int] = LimitOpt, dry_run: bool = DryRunOpt):
    """Run sensor ETL -> sensor_windows.parquet."""
    cfg = _load(config)
    raise typer.Exit(code=_run_stage(SensorETL(cfg), limit, dry_run))


@app.command()
def text(config: str = ConfigOpt, limit: Optional[int] = LimitOpt, dry_run: bool = DryRunOpt):
    """Run text ETL -> text_chunks.parquet."""
    cfg = _load(config)
    raise typer.Exit(code=_run_stage(TextETL(cfg), limit, dry_run))


@app.command()
def video(config: str = ConfigOpt, limit: Optional[int] = LimitOpt, dry_run: bool = DryRunOpt):
    """Run video ETL -> video_index.parquet (needs ffmpeg; skips cleanly if absent)."""
    cfg = _load(config)
    raise typer.Exit(code=_run_stage(VideoETL(cfg), limit, dry_run))


@app.command()
def assemble(config: str = ConfigOpt, limit: Optional[int] = LimitOpt, dry_run: bool = DryRunOpt):
    """Join the three indices -> incidents.parquet."""
    cfg = _load(config)
    try:
        raise typer.Exit(code=_run_stage(IncidentAssembler(cfg), limit, dry_run))
    except AssemblyError as exc:
        typer.secho(f"Assembly error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


@app.command("all")
def run_all(config: str = ConfigOpt, limit: Optional[int] = LimitOpt, dry_run: bool = DryRunOpt):
    """Run sensor -> text -> video -> assemble in order."""
    cfg = _load(config)
    for name, stage in (("sensor", SensorETL(cfg)), ("text", TextETL(cfg)),
                        ("video", VideoETL(cfg))):
        summ = stage.run(limit=limit, dry_run=dry_run)
        typer.secho(str(summ), fg=typer.colors.GREEN if summ.ok else typer.colors.YELLOW)
    try:
        summ = IncidentAssembler(cfg).run(limit=limit, dry_run=dry_run)
        typer.secho(str(summ), fg=typer.colors.GREEN if summ.ok else typer.colors.YELLOW)
    except AssemblyError as exc:
        typer.secho(f"Assembly error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    raise typer.Exit(code=0)


@app.command()
def evaluate(config: str = ConfigOpt,
             tier: str = typer.Option("mvp", "--tier", help="mvp | extended")):
    """Compute dataset-quality metrics and grade PASS/WARN/FAIL."""
    cfg = _load(config)
    if not Path(cfg.paths.incidents_index).exists():
        typer.secho("No incidents.parquet — run `assemble` (or `all`) first.",
                    fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    rep = evaluate_build(cfg, tier=tier, write=True)
    typer.echo(f"\n=== Evaluation ({tier}) — GRADE: {rep.grade} ===")
    for k, v in rep.metrics.items():
        typer.echo(f"  {k}: {v}")
    for f in rep.failures:
        typer.secho(f"  FAIL: {f}", fg=typer.colors.RED)
    for w in rep.warnings:
        typer.secho(f"  WARN: {w}", fg=typer.colors.YELLOW)
    color = {"PASS": typer.colors.GREEN, "WARN": typer.colors.YELLOW,
             "FAIL": typer.colors.RED}[rep.grade]
    typer.secho(f"GRADE: {rep.grade}", fg=color)
    raise typer.Exit(code=0 if rep.grade != "FAIL" else 1)


def main() -> None:  # pragma: no cover - thin wrapper
    try:
        app()
    except PipelineError as exc:
        typer.secho(f"Pipeline error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    main()
