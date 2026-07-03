"""Runtime incident retriever (Build Phase 6).

Builds a query from REAL incident context (failure family + the Phase 3/4
sensor summary: RMS trend, anomaly scores, important interval), searches the
vector store, and boosts hits whose topic tags match the configured
failure→topic map (graph metadata). Output evidence carries the chunk id as
its evidence_id — resolvable in the evidence graph (I-2).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

TOPIC_BOOST = 0.05


def sensor_summary_text(feature_rows: pd.DataFrame) -> str:
    """One-sentence real sensor summary from the per-window feature table."""
    if feature_rows is None or feature_rows.empty:
        return "no sensor feature summary available"
    first = feature_rows.iloc[0]
    last = feature_rows.iloc[-1]
    delta = (float(last["rms"]) - float(first["rms"])) / float(first["rms"]) \
        if float(first["rms"]) else 0.0
    trend = "rose" if delta > 0.05 else ("fell" if delta < -0.05 else "held steady")
    imp = feature_rows.loc[feature_rows["rms"].idxmax()]
    return (f"vibration RMS {trend} ({float(first['rms']):.0f} to "
            f"{float(last['rms']):.0f}) across {len(feature_rows)} sub-windows; "
            f"peak activity {float(imp['important_start_s']):.1f}s to "
            f"{float(imp['important_end_s']):.1f}s; "
            f"kurtosis up to {float(feature_rows['kurtosis'].max()):.1f}")


@dataclass(frozen=True)
class RetrievedEvidence:
    evidence_id: str          # == chunk_id; resolvable in the evidence graph
    citation: str
    score: float              # raw cosine
    boosted_score: float      # cosine + topic-map boost
    doc_type: str
    topic_tags: str
    text: str

    def to_dict(self) -> dict:
        return asdict(self)


class IncidentRetriever:
    def __init__(self, store, embedder, failure_to_topics: dict[str, list[str]]):
        store.require_embedder(embedder.name)
        self.store = store
        self.embedder = embedder
        self.failure_to_topics = failure_to_topics

    def build_query(self, incident: pd.Series, feature_rows: pd.DataFrame,
                    clip_summary: str | None = None) -> str:
        failure = str(incident.get("failure_family", "unknown")).replace("_", " ")
        parts = [f"CNC {failure} diagnosis and corrective action",
                 sensor_summary_text(feature_rows)]
        if clip_summary:
            parts.append(clip_summary)
        return "; ".join(parts)

    def retrieve(self, incident: pd.Series, feature_rows: pd.DataFrame,
                 k: int = 4, doc_type: str | None = None,
                 clip_summary: str | None = None) -> list[RetrievedEvidence]:
        query = self.build_query(incident, feature_rows, clip_summary)
        query_vec = self.embedder.embed([query], queries=True)[0]
        where = {"doc_type": doc_type} if doc_type else None
        hits = self.store.search(query_vec, k=max(k * 3, k), where=where)
        wanted = set(self.failure_to_topics.get(
            str(incident.get("failure_family", "unknown")), []))
        out = []
        for hit in hits:
            tags = set(str(hit.get("topic_tags", "")).split(",")) - {""}
            boost = TOPIC_BOOST * len(tags & wanted)
            out.append(RetrievedEvidence(
                evidence_id=str(hit["chunk_id"]),
                citation=str(hit.get("citation", hit["chunk_id"])),
                score=float(hit["score"]),
                boosted_score=float(hit["score"]) + boost,
                doc_type=str(hit.get("doc_type", "")),
                topic_tags=str(hit.get("topic_tags", "")),
                text=str(hit.get("text", "")),
            ))
        out.sort(key=lambda e: e.boosted_score, reverse=True)
        return out[:k]
