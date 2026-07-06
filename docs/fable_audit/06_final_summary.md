# 06 — Final Executive Summary (Fable audit, 2026-07-03)

## 1. What the codebase currently achieves

A working, test-covered **evidence workbench for CNC failure analysis**:
1,702 real incidents with vibration waveforms, per-window learned + heuristic
anomaly scores, real recovered good/bad run labels, BGE vector retrieval over
934 SOP/maintenance chunks, a 6,063-node evidence graph with resolve-or-raise
semantics (I-2), frozen-VLM summaries for all 20 linked clips, and 3,399
contract-valid aligned tuples (100% evidence resolution, 0 chronology
violations) — all rendered in a synchronized Streamlit workbench with JSON
evidence export. Build Phases 1–7 of 13 complete.

## 2. How it works

Single-YAML typed config → deterministic ETL → D10 sub-windowing → one-path
feature extraction (I-3) → seeded GPU encoder (Hvib) → BGE index → evidence
graph → frozen Qwen2.5-VL-3B clip summaries → temporal grounding joins
everything into `AlignedTuple`s → UI reads the parquet/JSON artifacts. Every
metric-producing step appends a run record (I-5/I-7).

## 3. Does it run?

**Yes.** Verified this session end-to-end: full pipeline commands, GPU model
runs (VLM 20/20 clips @ ~20 s/clip after a vision-token fix; grounding with
1,702 live BGE queries), dataset gate GRADE: PASS, and the app serving at
**http://localhost:8501** (healthz 200).

## 4. Test/build status

`pytest -q`: **209 passed, 1 skipped** (opt-in browser test) — unit,
integration (incl. a true E2E chain test with a broken-graph refusal case),
contract, eval-meta, and in-process UI render layers. `ruff`: clean.
Branch CI on GitHub Actions: not verified from here (issue F-10).

## 5. Key risks

Weak scaffolding labels (F-02, circularity), constructed video sync (F-05,
permanent caveat for this corpus), placeholder AUROC/ECE until Phase 12
(F-03), quarantine partially mechanical (F-04).

## 6. Top defects

None Critical. The register (05) lists 10 items: 2 High (both roadmap gaps,
not regressions), 4 Medium, 4 Low.

## 7. Missing capabilities (roadmap Phases 9–13)

Fusion/joint feature space, evidence-selection head, decoder LLM with GBNF
constrained decoding, real KPI-gate evaluation + faithfulness audit over
system outputs, one-command e2e demo, `scripts/eval_test.py`.

## 8. Recommended next phase

Commit the completed Phase 7 work (done immediately after this audit), then
**Phase 9: multimodal fusion baseline** (Hvib + Hvis-proxy + Htext joint
representation) — Phase 8's grounding slice was already pulled forward — with
the **gold mini-set curation (F-02) started in parallel**, since Phases 10+
metrics are blocked on it.

## 9. Approval checkpoint

PHASE COMPLETE. Waiting for user review and approval before making code changes.
