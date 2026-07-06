# 05 — Issue Register

| ID | Severity | Area | Issue | Evidence | Impact | Suggested Fix | Requires User Approval |
|---|---|---|---|---|---|---|---|
| F-01 | High (roadmap) | Explanation | No decoder LLM / GBNF constrained generation — `ExplanationOutput` has no producer; AI-claims UI is demo-badged | no `src/explain/`; `docs/_sdd/tasks.md` T-19+ | Core dissertation deliverable missing until Phase 11 | Build Phases 9–11 per roadmap (D2: Qwen2.5-7B Q4_K_M GGUF + llama.cpp GBNF) | Yes (next phases) |
| F-02 | High (science) | Labels | failure_family/severity are weak hash/amplitude scaffolding; any accuracy metric against them is circular (audit risk R-1) | `assemble_incidents.LabelDeriver.weak_*`; `manifest.json label_status` | Limits every learned-component claim | Curate gold mini-set on val (20–40 incidents) before Phase 10+ numbers are quoted | Yes (labeling effort) |
| F-03 | Medium | Eval | AUROC and ECE in `src/eval/metrics.py` are documented fixture placeholders; gates G3/G7–G11 unimplemented | `metrics.py:148-149,199-201`; `gates.yaml` | Fixture numbers could be misread as real | Phase 12 real implementations under the I-6 freeze process | Yes (I-6 process) |
| F-04 | Medium | Quarantine | I-4 is mechanically enforced only on the encoder token loader; other readers rely on convention; `scripts/eval_test.py` does not exist | `encoder/data.py::load_tokens` vs e.g. `read_parquet` callers | Accidental test-split read possible | Central quarantine guard + CI check in Phase 12 (planned, risk R-8) | No |
| F-05 | Medium | Video | Clip↔incident sync is constructed (label-matched); no measured-sync footage exists, so no visual claim can carry a within-incident timestamp | ledger/graph `sync_provenance=constructed`; risk R-2 | Caps temporal claims from video permanently for this corpus | Keep I-8 caveats (already embedded); acquire measured-sync clips if thesis needs video IoU | Yes (data collection) |
| F-06 | Medium | Encoder | Val AUROC 0.5798 on 21 positives (run-level labels) is a weak diagnostic; PatchTST raw-patch encoder unbuilt | run record; D13 | Anomaly ranking only modestly better than chance | More epochs/architectures in Phase 9+; gold labels (F-02) first | Yes |
| F-07 | Low | UI | Video sync is one-way (Streamlit `st.video` cannot report position); timeline bars not click-to-seek | `streamlit_app.py` design notes; UI docs | Cosmetic/interaction polish | Custom JS component if ever needed | Yes |
| F-08 | Low | Regimes | `regime_label` is `unknown` for all 1702 incidents | evaluate output `regime_dist` | Weakens video matching + mode_state in tuples | Derive from tags or drop (risk R-12) | Yes |
| F-09 | Low | Hygiene | `docs/` carries four generations of earlier generated doc sets with partially stale claims | `docs/{codebase_audit,context,build_iterations,refactor_ecosystem}` | Reader confusion only | Treat `fable_audit`/`architecture_audit` as canonical; archive later | No |
| F-10 | Low | Ops | Session interruptions kill background jobs and leave phases uncommitted (happened once); no CI evidence for the branch on GitHub Actions | this session's recovery; `.github/workflows/ci.yml` unverified on branch | Minor process risk | Commit at every gate (standing practice); check Actions run after push | No |

No Critical issues: the application, tests, and every implemented pipeline
stage run successfully end-to-end (see 04).
