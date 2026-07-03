# GPU Enablement Plan

## Purpose

Plan GPU enablement where it provides real value, while preserving CPU-first reliability.

## 1. Current GPU Detection Result

| Check | Result |
|---|---|
| Hardware | NVIDIA GeForce RTX 3060 |
| GPU memory | 12 GB |
| Driver | 595.79 |
| CUDA driver version | 13.2 |
| PyTorch | 2.6.0+cu124 |
| `torch.cuda.is_available()` | True |
| TensorFlow | 2.20.0 |
| TensorFlow GPUs | None |

## 2. CUDA/PyTorch/TensorFlow Readiness

PyTorch is GPU-ready on this machine. TensorFlow is not GPU-ready in the current environment. The project itself does not depend on either library.

## 3. Candidate GPU-Accelerated Modules

| Candidate | Recommendation | Rationale |
|---|---|---|
| Sensor event detection | Do not GPU-enable first | Current NumPy/Pandas tests pass and the workload is likely IO/Pandas-bound |
| Text embeddings | Good GPU candidate | If semantic retrieval is added, embedding batches can benefit from PyTorch CUDA |
| Vector search | Later candidate | FAISS CPU first; FAISS GPU only if corpus is large enough |
| Video transcoding | Possible later | ffmpeg GPU codecs add environment complexity and are not required for correctness |
| Model inference/training | Good future candidate | Downstream thesis modeling can use GPU, but not currently in repo scope |

## 4. CPU Fallback Strategy

GPU features must:

- Be optional
- Log selected device
- Fall back to CPU if CUDA is unavailable
- Avoid failing the full ETL when GPU libraries are absent
- Produce deterministic output independent of device where practical

## 5. Configuration Flag Design

Proposed config section after approval:

```yaml
compute:
  prefer_gpu: true
  device: auto        # auto | cpu | cuda
  batch_size: null    # null means choose safe default
```

UI should expose `prefer_gpu` only for features that use it.

## 6. Device Utility Design

Proposed function:

```python
def get_compute_device(prefer_gpu: bool = True) -> dict:
    """Return device selection metadata with CPU fallback."""
```

Return fields:

| Field | Meaning |
|---|---|
| `device` | `cuda` or `cpu` |
| `available` | Whether requested device is available |
| `name` | GPU name or CPU |
| `reason` | Fallback reason if any |
| `library` | Library used for detection, e.g. torch |

## 7. Batch-Size Guidance

For future embedding generation on a 12 GB RTX 3060:

| Workload | Starting Batch Size | Adjustment |
|---|---|---|
| Small sentence embeddings | 32 | Increase to 64 if memory stable |
| Long document chunks | 8-16 | Increase slowly |
| Model inference | model-dependent | Use try/except for OOM and reduce batch |

## 8. Memory-Safety Strategy

- Use bounded batches.
- Catch CUDA out-of-memory errors where practical.
- Clear temporary tensors between batches.
- Record peak batch size and runtime in logs.
- Provide CPU fallback with a clear warning.

## 9. Logging for GPU Usage

Log at run start:

- Requested device
- Selected device
- GPU name
- CUDA availability
- Batch size
- Fallback reason

## 10. Validation Tests for GPU Path

| Test | Method |
|---|---|
| CPU fallback | Mock CUDA unavailable |
| GPU selected | Mock CUDA available |
| Missing torch | Mock ImportError |
| Prefer CPU | `prefer_gpu=False` always returns CPU |
| Batch fallback | Simulate OOM and reduce batch or return actionable error |

## 11. Performance Benchmark Plan

| Benchmark | Input | Compare |
|---|---|---|
| Text embedding batch | 1k chunks | CPU vs GPU wall time |
| Vector search | 10k synthetic vectors | CPU vs GPU if FAISS GPU introduced |
| Sensor event detection | Large synthetic run | Current NumPy vs any proposed GPU path |

## Recommendation

Do not add GPU dependencies to the core ETL just to satisfy the existence of GPU hardware. Add the device abstraction in Stage B only if implementing embeddings, vector search, or model inference. The first practical GPU target is semantic text retrieval, not current sensor/video ETL.
