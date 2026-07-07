# Markdown Audit

## Purpose

Audit existing Markdown files for freshness, clarity, navigation, technical completeness, and missing topics.

## Audit Summary

| File | Strengths | Issues | Priority |
|---|---|---|---|
| `README.md` | Clear project purpose, quickstart, phase table, docs order | No Streamlit/GPU notes; raw-data/ffmpeg troubleshooting could be stronger | High |
| `CONTRIBUTING.md` | Practical setup, tests, code layout | No Streamlit/GPU/dev diagnostics; optional dependency absence not tied to commands | Medium |
| `docs/recipe_a_overview.md` | Excellent conceptual context and constraints | Still marked Phase 1; open questions include decisions now implemented | Medium |
| `docs/implementation_plan.md` | Good decomposition and risks | Stale because implementation exists; "gated on review" no longer reflects repo state | High |
| `docs/architecture.md` | Strong architecture and dataflow | Some future/target wording now overlaps with current code; no Streamlit/GPU discussion | High |
| `docs/software_design.md` | Detailed modules and test seams | Says signatures/pseudocode are design sketch, but code exists | High |
| `docs/test_strategy_and_plan.md` | Strong strategy and fixture plan | Does not record current local test result; no UI/GPU coverage plan | Medium |
| `docs/test_cases.md` | Matches current test IDs well | No Streamlit/GPU test cases | Medium |
| `docs/evaluation_criteria.md` | Strong acceptance metrics | Should mention current blocking state: no staged raw data/incidents locally | Low |

## Missing Documentation Topics

- Streamlit run instructions and UI workflow
- GPU availability, enable/disable, and CPU fallback
- ffmpeg installation and verification
- Optional dependency behavior for `tiktoken`, `pypdf`, `rank_bm25`
- Current test result and lint status
- Troubleshooting "No incidents.parquet"
- Difference between current topic-overlap retrieval and configured BM25 label
- Raw data staging checklist

## Markdown Standards Check

| Standard | Current State |
|---|---|
| Clear title | Present in all major Markdown files |
| Purpose section | Present in spirit, not always explicit |
| Prerequisites in setup docs | Present in README/CONTRIBUTING, needs ffmpeg/optional deps refinement |
| Run commands | Present |
| Test commands | Present |
| Architecture diagrams/references | Present in existing docs as text diagrams; Stage A adds Mermaid diagrams |
| GPU setup notes | Missing |
| Streamlit run instructions | Missing |
| Known limitations | Partly present; should be consolidated |

## Recommended Refactor Order

1. README
2. CONTRIBUTING
3. `config/dataset.yaml` comments
4. `docs/architecture.md`
5. `docs/software_design.md`
6. `docs/implementation_plan.md`
7. test and evaluation docs

No existing Markdown files were modified during Stage A.
