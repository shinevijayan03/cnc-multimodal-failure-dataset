# Phase 6 — Goal & Design (evidence graph + runtime retriever + real grounding)

User directives for this phase (2026-07-03): kill all processes; evaluate all
backend changes and update the UI; show real data, real results, **and real
temporal grounding** in the UI from now on; complete integration testing with
end-to-end test cases. Accordingly Phase 6 delivers its roadmap scope (DB-4)
**plus a pulled-forward slice of Phase 8** (the temporal-grounding producer),
because the grounding producer is what turns the new retriever into visible
end-to-end results.

## Components

| Piece | Design |
|---|---|
| `src/graph/evidence_graph.py` | NetworkX DiGraph + JSON persistence (D7). Node kinds: incident / window (SW_*) / chunk / doc / video / failure_family. Edges: has_window, linked_sop, linked_maintenance, part_of, video_matched (carries `sync_provenance=constructed`, I-8), classified_as (carries `label_status=weak_signal_derived`). `resolve(evidence_id)` returns node + in/out edges and **raises KeyError for unknown ids — this is the I-2 resolution service** (gate G2). |
| `src/retrieval/retriever.py` | `IncidentRetriever.retrieve(incident, feature_rows)`: builds a REAL query from failure family + `sensor_summary_text` (RMS trend across sub-windows, peak interval, kurtosis — Phase 3/4 features), vector-searches k×3 candidates, boosts by topic-tag ∩ failure_to_topics (+0.05/topic), returns ranked `RetrievedEvidence` whose evidence_id is the chunk id (graph-resolvable). |
| `src/temporal/grounding.py` | For every carved sub-window emits a contract-valid `AlignedTuple`: real sensor_summary (features + encoder score), clip_summary carrying the constructed-sync caveat in its text, retrieved_text from the runtime retriever, real alarm_state (event at t=0 inside span / pre / post), mode_state, the D10 span, and evidence_ids `[window, chunks, video]` — **any unresolvable id or chronology violation raises** rather than degrading. Persists `aligned_tuples.parquet`; appends a run record with the resolution metrics and a G2 gate entry. |
| UI | Grounded SOP bars replace demo SOP bars whenever tuples exist (bar = retrieved citation + real cosine score over the window span that queried it; source `grounded`, no demo badge); AI Explanation gains a "Grounded sensor chronology" section of real per-window summaries; a "Temporal grounding" panel shows the tuples table with provenance caption. |

## Honesty boundaries (I-7/I-8)

- SOP bar *time* = the sub-window whose context retrieved the chunk — a real
  retrieval association, labeled as such; not a document timestamp.
- Video linkage remains constructed; the caveat is inside every clip_summary.
- Claims row stays demo-badged until the Phase 11 decoder.
