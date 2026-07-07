# GPU Readiness Inventory

## Purpose

Record whether the current machine and project are ready for GPU-accelerated work.

## Hardware and Driver

| Check | Result |
|---|---|
| `nvidia-smi` | Available |
| GPU | NVIDIA GeForce RTX 3060 |
| GPU memory | 12288 MiB |
| Driver version | 595.79 |
| CUDA version reported by driver | 13.2 |
| Current memory use at check time | 924 MiB |

## Python GPU Libraries

| Library | Result |
|---|---|
| PyTorch | `2.6.0+cu124` installed |
| PyTorch CUDA availability | `True` |
| PyTorch device count | 1 |
| PyTorch device name | NVIDIA GeForce RTX 3060 |
| TensorFlow | `2.20.0` installed |
| TensorFlow GPUs | `[]` |

## Project GPU Usage

Current project source and dependency files do not declare or use:

- torch
- tensorflow
- CUDA-specific kernels
- cupy
- RAPIDS
- faiss/faiss-gpu
- ONNX Runtime GPU
- TensorRT
- transformers/sentence-transformers

## Fit for GPU Acceleration

| Candidate Area | Current Fit | Notes |
|---|---|---|
| Sensor event detection | Low to medium | Current NumPy/Pandas operations are likely CPU-sufficient unless processing large batches |
| Text embeddings/retrieval | High if embeddings are added | Could use sentence-transformers/PyTorch GPU for embedding generation |
| Vector search | Medium to high if corpus grows | Could use FAISS CPU first, FAISS GPU later |
| Video processing | Medium | ffmpeg can use GPU codecs, but current stage uses CPU ffmpeg and short clips |
| Model inference/training | High for future downstream model work | Not in current repository scope |

## Readiness Summary

The machine is GPU-ready for PyTorch workloads. The project itself is not GPU-enabled yet. Stage B should add a small device abstraction only if an approved feature actually benefits from GPU work, such as embedding generation or model inference. CPU fallback must remain the default-safe path.
