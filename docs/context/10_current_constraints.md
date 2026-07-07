# Current Constraints

## Performance Constraints

- Text ETL dry-run is bounded but still slow for quick validation. Evidence: `text --dry-run --limit 2` completes in about 35 seconds on the current staged manuals.
- Streamlit UI reads local Parquet artifacts; large artifact growth may affect UI load time. Inference based on `src/ui/incident_explorer.py` loading entire Parquet tables.

## Security Constraints

- No security/dependency audit tool is configured. Evidence: `requirements.txt`, `pyproject.toml`, `.github/workflows/ci.yml`.
- No required secrets or environment variables were found. Inference based on source/config scan.

## Infrastructure Constraints

- Local Windows/PowerShell environment is used in current validation.
- CI targets Ubuntu and Python 3.10 through 3.13. Evidence: `.github/workflows/ci.yml`.
- ffmpeg/ffprobe must be available on PATH for full video processing. Evidence: `requirements.txt`, `src/etl/video_etl.py`.

## Platform Limitations

- Current validation is on Python 3.12.7. Evidence: pytest output.
- Browser-level Streamlit smoke is configured as opt-in with `RUN_BROWSER_SMOKE=1`; deeper interaction checks are not configured by default.

## Repository Conventions

- Do not refactor before checkpointing the dirty working tree.
- Preserve Parquet schemas unless explicitly approved.
- Use `pytest`, `ruff`, `compileall`, evaluation, and runtime smoke as guardrails.
- Generated audit/context docs are stored under `docs/`.

## Technology Choices

- Python package with setuptools metadata in `pyproject.toml`.
- Typer CLI.
- Streamlit UI.
- pandas/pyarrow Parquet storage.
- Pydantic config/schema contracts.

## Business/Project Constraints

- Dataset quality matters for thesis/final claims. Evidence: evaluation grade is `PASS`, but labels are marked as weak deterministic scaffolding rather than curated ground truth.
- Raw data provenance/licensing must be verified before distribution. Status: Unknown.

## Non-Functional Requirements

Verified:
- Automated tests must pass.
- Local UI must respond.
- Evaluation must identify data-quality risks.

Open:
- Fast developer smoke path for text ETL.
- Browser interaction regression checks.
- Security/dependency audit baseline.
