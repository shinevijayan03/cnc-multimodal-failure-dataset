# Phase 3 — Design

## Feature path extension (`src/features/vibration.py`)

| Function | Behavior | Notes |
|---|---|---|
| `spectral_bands(values, fs, n_bands=4)` | Mean rFFT power in equal-width bands 0→Nyquist; signal mean-detrended so the DC mounting offset cannot dominate band 0; constant/empty → zeros | Contract fixes n=4 |
| `band_edges_hz(fs, n_bands)` | Band boundaries helper | — |
| `sliding_rms(x, fs, window_s, hop_s)` | **Moved verbatim** from `EventDetector._sliding_rms` (cumsum formulation) | Behavior-preserving by construction; agreement with per-window `rms()` asserted by meta-test |

`EventDetector._sliding_rms` is now a two-line delegate importing from the
feature path — the audit's R-5 duplication is retired. Numpy enters the
module; the original list-based functions are unchanged (eval fixtures and
UI keep working).

## Patcher (`src/features/patching.py`) — decision D12

- `patch_spec(n_samples, n_channels, fs, patch_s=0.25, stride_s=0.125)` →
  geometry; raises on windows shorter than one patch.
- `make_patches(window, fs, ...)` → `(n_patches, n_channels, patch_samples)`
  float64; incomplete tails dropped, never padded (mirrors D10).
- At 2 kHz a 12 s sub-window → 95 patches × 3 channels × 500 samples.
  The Phase 4 encoder consumes this tensor directly.

## Producer (`src/tgfx/sensor_features.py`)

- Iterates the Phase 2 sub-window index grouped by incident; loads each
  waveform once; joins `fs_hz` from `sensor_windows.parquet`.
- **Index-based slicing** (searchsorted + duration×fs samples) so float noise
  in the time column can never add/drop a sample (bug found and fixed in
  loop L3.1 — a mask-based slice yielded 24001 samples).
- Canonical signal (D12): tri-axial magnitude, median-removed.
- Per window: `rms`, `spectral_bands` (4), `kurtosis`, `variance` — all via
  the one feature path; `anomaly_score = Δ/(1+Δ)` of the RMS rise over the
  incident's earliest sub-window (`feature_delta`); `important_interval` =
  peak 1 s sliding-RMS segment; patch geometry; sha256 over the raw float64
  channel bytes.
- Contract conformance: full `SensorWindow` instances (with 24k-sample
  channel lists) are pydantic-validated for the first N windows per run
  (default 5). Validating all 3,399 full instances would burn minutes on
  pure pydantic list validation for zero extra information — the schema is
  identical across rows; unit tests validate synthetic instances exhaustively.
- Output: `sensor_features.parquet` (path key `paths.sensor_features_index`,
  defaulted in `PathsCfg`, explicit in both YAMLs).

## Alternatives rejected

- *Numpy feature math in the producer* — violates I-3; the pure-Python
  one-path functions cost ~2 min for the full corpus, acceptable.
- *Changing the ETL sliding-RMS to per-window `rms()` calls* — risks float
  drift flipping threshold comparisons and shifting incident IDs; moving the
  vectorized implementation wholesale is provably behavior-identical.
- *Persisting patch tensors* — 3399 × 95 × 3 × 500 float64 ≈ 3.9 GB; patches
  are recomputed on demand (deterministic), only geometry is persisted.
