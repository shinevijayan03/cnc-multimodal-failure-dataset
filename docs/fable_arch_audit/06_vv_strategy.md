# 06 — V&V Strategy (for the remaining builds)

Per phase (ETVX): static (ruff) → focused unit tests → full `pytest -q` →
runtime (CLI JSON summaries + Streamlit healthz + AppTest render/interaction)
→ diff review (`git diff --stat/--check`) → user gate. Every metric appends a
seeded run record (I-5/I-7); no val KPI regression merges (I-10).

| Build | Key V&V (beyond the standard loop) |
|---|---|
| A (fusion/selection) | selection determinism; every selected id graph-resolves (G2); bundle↔tuple cross-consistency; E2E chain test extended |
| B (decoder) | schema_valid_rate = 1.0 via mock AND via GBNF path (gate G1); every ChainClaim evidence_id resolves (I-2 → G2); rule-based sensor verifier agreement; B1 free-text baseline measurably worse on validity; latency budget on the 3060 |
| C (UI) | AppTest: click-evidence → highlighted source; panel render; regression on playback state tests |
| D (audit) | meta-tests re-run green after any `src/eval/` change (I-6); corrupted-output fixtures must degrade scores; prior runs re-scored bit-identically |
| E (SOP upload) | security tests: file-type allowlist, size cap, path traversal rejection, no execution of uploaded content; OCR golden-file test; tagging precision spot-set |
| F (hardening) | full suite + coverage; dependency audit; dead-code sweep; final architecture-compliance matrix re-scored against `03_…gap_matrix.md` |

Standing invariants checked every phase: I-1 (no VLM gradients), I-3 (feature
math only via `src/features/vibration.py` — agreement meta-test), I-4 (test
split refused mechanically; extend guard in Build-D), I-8 (constructed-sync
caveat present in any video-derived surface).

Subagent use (per fable_prompt policy): security_reviewer at Build-E;
diff_reviewer optional at each gate; others unnecessary — parent context
already holds verified maps.
