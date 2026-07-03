# GPU Environment Report

## Purpose

Capture the exact GPU checks requested for Stage A.

## `nvidia-smi`

```text
NVIDIA-SMI 595.79
Driver Version: 595.79
CUDA Version: 13.2
GPU 0: NVIDIA GeForce RTX 3060
Memory: 924 MiB / 12288 MiB at check time
Compute mode: Default
```

## Python GPU Library Check

Command run:

```bash
python - <<'PY'
try:
    import torch
    print("torch:", torch.__version__)
    print("cuda_available:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("device_count:", torch.cuda.device_count())
        print("device_name:", torch.cuda.get_device_name(0))
except Exception as e:
    print("torch_check_error:", e)

try:
    import tensorflow as tf
    print("tensorflow:", tf.__version__)
    print("gpus:", tf.config.list_physical_devices("GPU"))
except Exception as e:
    print("tensorflow_check_error:", e)
PY
```

Result:

```text
torch: 2.6.0+cu124
cuda_available: True
device_count: 1
device_name: NVIDIA GeForce RTX 3060
tensorflow: 2.20.0
gpus: []
```

Observed warning:

```text
The pynvml package is deprecated. Please install nvidia-ml-py instead.
```

TensorFlow also emitted oneDNN informational messages. They do not block Stage A.

## Interpretation

- PyTorch can use the GPU.
- TensorFlow is installed but does not see a GPU.
- The current project does not depend on either library.
- GPU enablement should be opt-in and isolated behind a utility such as `get_compute_device(prefer_gpu=True)` if Stage B introduces embedding/model workloads.
