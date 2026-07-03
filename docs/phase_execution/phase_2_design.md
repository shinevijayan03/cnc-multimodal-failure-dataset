# Phase 2 — Design

## Placement

`src/tgfx/windows.py` — the TGFX substrate package already owns the
dataset-facing artifacts (`src/tgfx/dataset.py`); sub-window carving is
dataset-shaped (no features, no learning), so it lands beside it. Phase 3
(patching/features) and Phase 8 (temporal grounding) will import from here —
one authoritative window implementation, mirroring the I-3 one-feature-path
principle at the windowing level.

## Structure (matches repo idiom: pure numeric core + thin IO driver)

| Layer | Function | Behavior |
|---|---|---|
| Constants | `INCIDENT_SPAN=(-60,30)`, `SUB_WINDOW_S=12`, `SUB_WINDOW_STRIDE_S=3`, `QUERY_WINDOW=(-12,0)` | Single source for D1/D10 numbers |
| Pure core | `carve_subwindows(incident_id, available_span)` | Clip span to bounds; emit windows while `start+12 <= hi+eps`; **short span → zero windows** (contract demands exactly 12.0 s; D10 forbids padding) |
| Pure core | `resolve_query_window(available_span)` | Clip [-12,0] to available span; return coverage fraction + clipped flag; no overlap → empty window, coverage 0 |
| IDs | `sensor_evidence_id(incident_id, ordinal)` → `SW_<id>_<NN>` | Byte-compatible with `src/eval/fixtures.py` (`SW_inc_oracle_001_00`) |
| Driver | `build_subwindow_frame(sensor_index, repo_root)` | Reads each per-incident waveform's `t_rel_s` span; joins core outputs; short-span incidents get one row with null `window_id` so they stay visible |
| Entrypoint | `build_subwindow_index(cfg)` / `python -m src.tgfx.windows` | Writes `cfg.paths.subwindows_index` atomically; prints JSON summary |

## Config change

`PathsCfg.subwindows_index` added with a default (`src/common/config.py`) —
old configs stay valid; both YAML configs list the key explicitly per repo
convention.

## Alternatives rejected

- *Emitting full `SensorWindow` contract instances now* — requires rms /
  4-band spectral energy / kurtosis / variance / sha256, which is exactly
  Phase 3's feature work; emitting spans-only avoids duplicating feature math
  ahead of the I-3 unification.
- *Changing the ETL's ±8 s carving* — D10 keeps the ETL as incident-span
  producer; the staged corpus (20 s runs) cannot honor [-60,+30] anyway, so
  the sub-window layer records coverage instead of forcing a rebuild.
- *Hash-based window IDs* (like `incident_id`) — ordinal IDs are the scheme
  the eval fixtures already resolve; determinism comes from the deterministic
  carve order.
