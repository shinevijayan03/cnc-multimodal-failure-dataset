"""Evidence graph — nodes/edges across incidents, windows, chunks, video (D7).

NetworkX DiGraph + JSON persistence (decision D7: Neo4j is a non-goal).
The graph is the evidence-ID resolution service behind constitution I-2:
every evidence_id emitted anywhere must resolve here, and `resolve` raising
KeyError is exactly what "unresolvable claim" means downstream.

Node kinds: incident, window (SW_*), chunk, doc, video, failure_family.
Edge relations: has_window, linked_sop, linked_maintenance, part_of,
video_matched (attrs carry sync_provenance), classified_as.

Usage:
    python -m src.graph.evidence_graph --config config/dataset.yaml
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import networkx as nx
import pandas as pd

from src.common.config import PipelineConfig, load_config
from src.common.io_utils import load_json_col, read_parquet

GRAPH_FILENAME = "evidence_graph.json"


class EvidenceGraph:
    def __init__(self, graph: nx.DiGraph | None = None):
        self.g = graph or nx.DiGraph()

    # ------------------------------------------------------------------ build
    def add_node(self, node_id: str, kind: str, **attrs) -> None:
        self.g.add_node(str(node_id), kind=kind, **attrs)

    def add_edge(self, src: str, dst: str, rel: str, **attrs) -> None:
        for node in (src, dst):
            if node not in self.g:
                raise KeyError(f"edge endpoint not in graph: {node}")
        self.g.add_edge(str(src), str(dst), rel=rel, **attrs)

    # ------------------------------------------------------------------ query
    def __len__(self) -> int:
        return self.g.number_of_nodes()

    @property
    def n_edges(self) -> int:
        return self.g.number_of_edges()

    def resolve(self, evidence_id: str) -> dict:
        """Resolve an evidence id to its node + linked context (backs I-2)."""
        node_id = str(evidence_id)
        if node_id not in self.g:
            raise KeyError(f"evidence id does not resolve in the graph: {node_id}")
        data = dict(self.g.nodes[node_id])
        out_edges = [{"to": v, "rel": d.get("rel"), **{k: x for k, x in d.items()
                                                       if k != "rel"}}
                     for _, v, d in self.g.out_edges(node_id, data=True)]
        in_edges = [{"from": u, "rel": d.get("rel")}
                    for u, _, d in self.g.in_edges(node_id, data=True)]
        return {"id": node_id, **data, "out": out_edges, "in": in_edges}

    def resolves(self, evidence_id: str) -> bool:
        return str(evidence_id) in self.g

    def neighbors(self, node_id: str, rel: str | None = None) -> list[str]:
        return [v for _, v, d in self.g.out_edges(str(node_id), data=True)
                if rel is None or d.get("rel") == rel]

    def kind_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for _, data in self.g.nodes(data=True):
            counts[data.get("kind", "?")] = counts.get(data.get("kind", "?"), 0) + 1
        return counts

    # ------------------------------------------------------------------ persistence
    def save(self, path: str | Path) -> None:
        payload = nx.node_link_data(self.g, edges="edges")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(payload, sort_keys=True),
                              encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "EvidenceGraph":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(nx.node_link_graph(payload, directed=True, edges="edges"))


def graph_path(cfg: PipelineConfig) -> Path:
    return Path(cfg.paths.data_processed) / GRAPH_FILENAME


def build_graph(cfg: PipelineConfig) -> EvidenceGraph:
    """Assemble the graph from the real pipeline artifacts."""
    incidents = read_parquet(cfg.paths.incidents_index)
    chunks = read_parquet(cfg.paths.text_chunks)
    subwindows_path = Path(cfg.paths.subwindows_index)
    subwindows = (read_parquet(subwindows_path)
                  if subwindows_path.exists() else pd.DataFrame())
    graph = EvidenceGraph()

    for _, chunk in chunks.iterrows():
        doc_id = str(chunk["doc_id"])
        if not graph.resolves(doc_id):
            graph.add_node(doc_id, "doc")
        graph.add_node(str(chunk["chunk_id"]), "chunk",
                       doc_type=str(chunk["doc_type"]),
                       topic_tags=",".join(str(t) for t in
                                           load_json_col(chunk["topic_tags"])))
        graph.add_edge(str(chunk["chunk_id"]), doc_id, "part_of")

    for _, inc in incidents.iterrows():
        inc_id = str(inc["incident_id"])
        family = f"failure:{inc.get('failure_family', 'unknown')}"
        if not graph.resolves(family):
            graph.add_node(family, "failure_family")
        graph.add_node(inc_id, "incident",
                       split=str(inc.get("split", "unknown")),
                       severity=str(inc.get("severity_label", "unknown")))
        graph.add_edge(inc_id, family, "classified_as",
                       label_status="weak_signal_derived")
        video_file = inc.get("video_file")
        if video_file is not None and pd.notna(video_file) and str(video_file):
            vid = str(video_file)
            if not graph.resolves(vid):
                graph.add_node(vid, "video")
            graph.add_edge(inc_id, vid, "video_matched",
                           sync_provenance="constructed",
                           method=str(inc.get("alignment_method", "unknown")))
        for rel, column in (("linked_sop", "sop_chunk_ids"),
                            ("linked_maintenance", "maintenance_chunk_ids")):
            for chunk_id in load_json_col(inc.get(column)):
                if graph.resolves(str(chunk_id)):
                    graph.add_edge(inc_id, str(chunk_id), rel,
                                   method="keyword_topic_build_time")

    if not subwindows.empty:
        carved = subwindows[subwindows["window_id"].notna()]
        for _, sub in carved.iterrows():
            window_id = str(sub["window_id"])
            inc_id = str(sub["incident_id"])
            graph.add_node(window_id, "window",
                           t_start=float(sub["t_start"]),
                           t_end=float(sub["t_end"]))
            if graph.resolves(inc_id):
                graph.add_edge(inc_id, window_id, "has_window")
    return graph


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the evidence graph.")
    parser.add_argument("--config", default="config/dataset.yaml")
    parser.add_argument("--resolve", default=None,
                        help="Resolve one evidence id and exit")
    args = parser.parse_args(argv)
    cfg = load_config(args.config)
    out = graph_path(cfg)
    if args.resolve:
        graph = EvidenceGraph.load(out)
        print(json.dumps(graph.resolve(args.resolve), indent=2, sort_keys=True,
                         default=str))
        return 0
    graph = build_graph(cfg)
    graph.save(out)
    print(json.dumps({"nodes": len(graph), "edges": graph.n_edges,
                      "kinds": graph.kind_counts(), "out": out.as_posix()},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
