# Software Design — Recipe A Pipeline

**Status:** Phase 1 (design). Signatures/pseudocode below are a *design sketch*
to be reviewed — not implementation. **Companion:** [Architecture](architecture.md)
· [Implementation Plan](implementation_plan.md).

Covers: data models, module/function design with signatures, error-handling
strategy, configuration strategy, extensibility hooks, and the design-unit→file map.

---

## 1. Design-unit → file map

| File | Units (classes / key functions) |
|------|---------------------------------|
| `src/common/config.py` | `load_config()`, `PipelineConfig` + nested config models |
| `src/common/schemas.py` | `SensorWindowRow`, `VideoIndexRow`, `TextChunkRow`, `IncidentRow`; enums |
| `src/common/io_utils.py` | `write_parquet_atomic()`, `read_parquet()`, `dump_json_col()`, `load_json_col()`, `resolve_path()`, `exists_and_fresh()` |
| `src/common/ids.py` | `incident_id()`, `video_id()`, `chunk_id()`, `stable_hash()` |
| `src/common/logging_utils.py` | `get_logger()`, `RunSummary` |
| `src/etl/sensor_etl.py` | `SensorETL`; `Normalizer`, `FsEstimator`, `EventDetector`, `WindowCarver`, `EvidenceSpanExtractor`; `READERS` registry |
| `src/etl/text_etl.py` | `TextETL`; `DocReader`, `Chunker`, `TopicTagger` |
| `src/etl/video_etl.py` | `VideoETL`; `FfprobeReader`, `FfmpegNormalizer`, `TagMerger` |
| `src/etl/assemble_incidents.py` | `IncidentAssembler`; `LabelDeriver`, `VideoMatcher`, `TextRetriever`, `SplitAssigner` |
| `src/cli.py` | `app` (Typer) with `sensor/text/video/assemble/all/evaluate` |
| `src/evaluate.py` | `compute_metrics()`, `render_report()` |

---

## 2. Data models (`src/common/schemas.py`)

Pydantic v2 models. JSON-list fields are stored as JSON strings in Parquet and
(de)serialized at the IO boundary. Enums keep label vocabularies closed & typed.

```python
from enum import Enum
from pydantic import BaseModel, Field, field_validator

class FailureFamily(str, Enum):
    tool_wear = "tool_wear"; chatter = "chatter"; clamping_loss = "clamping_loss"
    coolant_fault = "coolant_fault"; spindle_fault = "spindle_fault"; unknown = "unknown"

class Regime(str, Enum):
    roughing="roughing"; finishing="finishing"; plunge="plunge"; idle="idle"
    drilling="drilling"; contouring="contouring"; unknown="unknown"

class Condition(str, Enum):
    normal="normal"; tool_wear_visible="tool_wear_visible"; heavy_vibration="heavy_vibration"
    coolant_issue="coolant_issue"; chatter="chatter"; chip_packing="chip_packing"; unknown="unknown"

class DocType(str, Enum):
    sop="sop"; maintenance="maintenance"

class Severity(str, Enum):
    low="low"; med="med"; high="high"; unknown="unknown"

class Split(str, Enum):
    train="train"; val="val"; test="test"; human_eval="human_eval"

class AlignmentMethod(str, Enum):
    label_match="label_match"; idle_fallback="idle_fallback"; none="none"

class Span(BaseModel):                # evidence interval, incident-relative seconds
    start_s: float
    end_s: float
    @field_validator("end_s")
    @classmethod
    def _ordered(cls, v, info):
        if v < info.data["start_s"]: raise ValueError("end_s < start_s")
        return v

class SensorWindowRow(BaseModel):
    incident_id: str
    source_dataset: str
    machine_family: str
    failure_family: FailureFamily = FailureFamily.unknown
    window_start_s: float           # in original run time
    window_end_s: float
    fs_hz: float
    sensor_file: str                # path to per-incident parquet
    sensor_channels: list[str]
    sensor_relevant_spans: list[Span] = []
    n_samples: int | None = None

class VideoIndexRow(BaseModel):
    video_id: str
    video_file: str
    video_fps: float
    duration_s: float
    regime_label: Regime = Regime.unknown
    condition_label: Condition = Condition.unknown
    source: str                     # own | stock | youtube_cc | ...

class TextChunkRow(BaseModel):
    doc_id: str
    chunk_id: str
    doc_type: DocType
    text: str
    topic_tags: list[str] = []
    n_tokens: int

class IncidentRow(BaseModel):
    incident_id: str
    source_dataset: str
    machine_family: str
    failure_family: FailureFamily
    window_start_s: float
    window_end_s: float
    fs_hz: float
    sensor_file: str
    sensor_channels: list[str]
    sensor_relevant_spans: list[Span]
    video_file: str | None
    video_fps: float | None
    video_relevant_spans: list[Span] = []
    sop_chunk_ids: list[str] = []
    maintenance_chunk_ids: list[str] = []
    phase_label: str = "unknown"
    regime_label: Regime = Regime.unknown
    severity_label: Severity = Severity.unknown
    root_cause_label: str = "unknown"
    alignment_method: AlignmentMethod = AlignmentMethod.none   # provenance flag
    split: Split
```

**Why Pydantic enums + JSON-list fields:** closed label vocabularies catch typos
at the boundary; JSON-list-as-string keeps Parquet flat and portable (no nested
Arrow types needed) while remaining query-able after a one-line decode.

---

## 3. Configuration (`src/common/config.py`)

```python
class WindowingCfg(BaseModel):
    pre_event_s: float = 60.0; post_event_s: float = 30.0
    drop_partial_windows: bool = True; max_windows_per_run: int | None = None

class EventDetectionCfg(BaseModel):
    method: str = "rms_threshold"; channel_for_energy: str = "az"
    window_s: float = 1.0; hop_s: float = 0.25
    threshold_kind: str = "zscore"; threshold_value: float = 3.0
    baseline_window_s: float = 30.0
    min_event_separation_s: float = 30.0; min_event_duration_s: float = 0.5

class SensorDatasetCfg(BaseModel):
    name: str; enabled: bool = True; path: str; reader: str
    machine_family: str = "cnc_mill"; fs_hz: float | None = None
    column_map: dict[str, str] = {}

# ... VideoCfg, TextCfg, AssembleCfg, RuntimeCfg, PathsCfg analogous ...

class PipelineConfig(BaseModel):
    version: str; random_seed: int = 1337
    paths: PathsCfg; sensor: SensorCfg; video: VideoCfg
    text: TextCfg; assemble: AssembleCfg; runtime: RuntimeCfg

def load_config(path: str | Path) -> PipelineConfig:
    """Parse YAML, validate into PipelineConfig, resolve relative paths to
    absolute against repo root, check supported `version`. Raises ConfigError
    with the exact offending key on failure."""
```

**Strategy:** parse-once → validate → pass the typed object explicitly into each
stage (no global singletons → testable, override-able per run).

---

## 4. Shared IO & ids

```python
# io_utils.py
def write_parquet_atomic(df: pd.DataFrame, path: Path) -> None: ...   # temp→fsync→rename
def read_parquet(path: Path) -> pd.DataFrame: ...
def dump_json_col(values: list) -> str: ...        # list[Span|str] -> json string
def load_json_col(s: str) -> list: ...
def resolve_path(p: str | Path, root: Path) -> Path: ...
def exists_and_fresh(out: Path, *inputs: Path) -> bool: ...  # idempotency / skip

# ids.py
def stable_hash(*parts: str) -> str: ...                     # short sha1 hex
def incident_id(source_dataset: str, run_id: str, t_event_s: float) -> str: ...
def video_id(source: str, rel_path: str) -> str: ...
def chunk_id(doc_id: str, ordinal: int) -> str: ...
```

Deterministic ids are the backbone of idempotency: the same input always yields
the same id, so `exists_and_fresh` can safely skip already-built outputs.

---

## 5. Sensor ETL (`src/etl/sensor_etl.py`)

```python
READERS: dict[str, Callable[[Path, dict], Iterator[RawRun]]] = {
    "generic_csv": read_generic_csv,
    "bosch_h5":    read_bosch_h5,
    # register new formats here — extensibility hook #1
}

@dataclass
class RawRun:
    run_id: str
    df: pd.DataFrame            # raw columns
    meta: dict                  # source-provided fs, labels, etc.

class Normalizer:
    def __init__(self, cfg: SensorCfg): ...
    def normalize(self, run: RawRun, column_map: dict[str, str]) -> pd.DataFrame:
        """Rename via column_map → canonical [time_s, ax, ay, az, *optional];
        coerce dtypes; build/repair monotonic time_s; drop unmapped columns."""

class FsEstimator:
    def estimate(self, df: pd.DataFrame, meta: dict, cfg) -> float:
        """median_dt | metadata | fixed. Validate against [min,max]_plausible_hz."""

class EventDetector:
    def detect(self, df: pd.DataFrame, fs_hz: float, cfg: EventDetectionCfg) -> list[Event]:
        """Sliding RMS over channel_for_energy → rolling baseline → z-score →
        threshold crossings → merge(min_separation) → filter(min_duration).
        Returns Event(t_event_s, t_start_s, t_end_s, score)."""

class WindowCarver:
    def carve(self, df, event: Event, fs_hz, cfg: WindowingCfg) -> Window | None:
        """Slice [t_event-pre, t_event+post]; add t_rel_s = time_s - t_event;
        return None if partial and drop_partial_windows."""

class EvidenceSpanExtractor:
    def extract(self, window, event, cfg) -> list[Span]:
        """threshold_crossings | top_k_energy → padded, capped spans (rel time)."""

class SensorETL:
    def __init__(self, cfg: PipelineConfig, logger): ...
    def run(self, limit: int | None = None, dry_run: bool = False) -> RunSummary:
        """For each enabled dataset → READERS[reader] → per run:
        normalize → fs → detect → for each event: carve → spans →
        write window parquet + SensorWindowRow. Append index; write atomically."""
```

**Numeric core kept pure & testable:** `EventDetector.detect`,
`WindowCarver.carve`, `FsEstimator.estimate` are pure functions of arrays/config
(no IO) → unit-tested with synthetic signals (see [Test Cases](test_cases.md)).

---

## 6. Text ETL (`src/etl/text_etl.py`)

```python
class DocReader:
    def read(self, path: Path) -> tuple[str, DocType]:
        """md/txt/docx → plain text (keep headings as markers); infer doc_type
        from path/front-matter."""

class Chunker:
    def __init__(self, cfg: ChunkingCfg, tokenizer): ...
    def chunk(self, text: str) -> list[str]:
        """Split on heading/paragraph; greedily pack to ~target_tokens with
        overlap; never cross headings; hard-split paragraphs > max_tokens."""
    def count_tokens(self, s: str) -> int: ...      # tiktoken | whitespace fallback

class TopicTagger:
    def __init__(self, topic_keywords: dict[str, list[str]]): ...
    def tag(self, text: str) -> list[str]:          # keyword → topic tags

class TextETL:
    def run(self, limit=None, dry_run=False) -> RunSummary:
        """glob manuals → read → chunk → tag → TextChunkRow → text_chunks.parquet"""
```

**Extensibility hook #2:** `tokenizer` and `TopicTagger` are injectable; an
embedding tagger can replace keyword tagging without touching `TextETL`.

---

## 7. Video ETL (`src/etl/video_etl.py`)

```python
class FfprobeReader:
    def probe(self, path: Path) -> dict:            # fps, duration_s, codec, h/w

class FfmpegNormalizer:
    def __init__(self, cfg: NormalizeCfg): ...
    def normalize(self, src: Path, dst: Path) -> None:
        """Skip if already conformant (probe); else ffmpeg → 720p/30fps/H.264.
        Raises VideoToolError if ffmpeg missing/fails."""

class TagMerger:
    def merge(self, video_id: str, tags_csv: pd.DataFrame) -> tuple[Regime, Condition, str]:
        """Look up human regime/condition/source; default unknown if absent."""

class VideoETL:
    def run(self, limit=None, dry_run=False) -> RunSummary:
        """discover mp4 → probe → normalize → merge tags → VideoIndexRow →
        video_index.parquet"""
```

---

## 8. Incident Assembly (`src/etl/assemble_incidents.py`)

```python
class LabelDeriver:
    def derive(self, sw: SensorWindowRow, cfg) -> dict:
        """regime/phase/severity/root_cause from dataset meta + amplitude
        quantiles; default 'unknown'."""

class VideoMatcher:
    def __init__(self, video_idx: pd.DataFrame, cfg: VideoMatchCfg, rng): ...
    def match(self, regime: Regime, condition: Condition) -> tuple[VideoIndexRow|None, AlignmentMethod]:
        """filter by regime (± condition) → seeded pick; idle fallback;
        returns (clip, alignment_method)."""

class TextRetriever:
    def __init__(self, chunks: pd.DataFrame, cfg: TextRetrievalCfg): ...
    def retrieve(self, failure: FailureFamily, doc_type: DocType, k_range) -> list[str]:
        """failure→topics; BM25/keyword over doc_type chunks; return [min,max] ids."""

class SplitAssigner:
    def __init__(self, fractions: dict, group_key: str, rng): ...
    def assign(self, rows: list[IncidentRow]) -> None:   # grouped, seeded, in place

class IncidentAssembler:
    def run(self, limit=None, dry_run=False) -> RunSummary:
        """load 3 indices (fail-fast if missing); per sensor window:
        derive labels → match video → retrieve sop+maint chunks → carry spans →
        build IncidentRow; then SplitAssigner; write incidents.parquet."""
```

**Extensibility hook #3:** `VideoMatcher` / `TextRetriever` are strategy objects;
swap `label_match`→similarity or `keyword`→embedding via config without changing
the assembler.

---

## 9. CLI (`src/cli.py`)

```python
app = typer.Typer()
@app.command()
def sensor(config: Path = "config/dataset.yaml", limit: int | None = None, dry_run: bool = False): ...
@app.command()
def text(...): ...
@app.command()
def video(...): ...
@app.command()
def assemble(...): ...
@app.command()
def all(...): ...        # sensor→text→video→assemble; stop on fatal
@app.command()
def evaluate(...): ...
```

Each command: `load_config` → build stage → `stage.run(...)` → print `RunSummary`
→ exit code from summary status.

---

## 10. Error-handling strategy

| Layer | Policy |
|-------|--------|
| **Config** | `ConfigError` at load; names the offending key; aborts (can't proceed). |
| **Per-file/run** | caught, logged with context, counted as `skipped`; loop continues — unless `runtime.fail_fast`. |
| **Validation** | Pydantic `ValidationError` on a row → that item skipped + logged; never write an invalid row. |
| **External tools** | `VideoToolError` (ffmpeg missing/fail) isolated to video stage with install hint. |
| **Missing upstream** | assembler fails fast naming the command to run first. |
| **Determinism** | all randomness via a single seeded `rng`; no bare `random`/`np.random` calls. |

Custom exceptions: `ConfigError`, `ReaderError`, `VideoToolError`,
`AssemblyError` (all subclass `PipelineError`).

---

## 11. Extensibility hooks (summary)

1. **New sensor format** → add a reader to `READERS` + a `column_map` in config.
   No core change.
2. **New text tagging/retrieval** → inject a different `TopicTagger` / swap
   `TextRetriever` strategy (keyword → embedding/BM25).
3. **New video matching** → swap `VideoMatcher` strategy (label → visual-similarity).
4. **New event detector** → register under `event_detection.method`.
5. **New label/severity logic** → `LabelDeriver` is the single choke point.

---

## 12. Testing seams (informs [Test Strategy](test_strategy_and_plan.md))

- Pure numeric functions (detect/carve/fs/chunk/split) take arrays+config, no IO
  → fast unit tests.
- IO isolated in `io_utils` + reader functions → mock/tmp-dir tested.
- `ffmpeg` wrapped in `FfmpegNormalizer` → mock subprocess in unit tests; real
  ffmpeg only in one integration test.
- Each stage's `run()` returns a `RunSummary` → integration tests assert on
  counts without scraping logs.
