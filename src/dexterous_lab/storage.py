"""Project-controlled storage on the GPUFree data volume."""

from pathlib import Path

from dexterous_lab.config import PROJECT_ROOT


DATA_ROOT = PROJECT_ROOT


def storage_environment():
    return {
        "TMPDIR": str(DATA_ROOT / "assets/cache"),
        "XDG_CACHE_HOME": str(DATA_ROOT / ".cache"),
        "XDG_DATA_HOME": str(DATA_ROOT / ".local/share"),
        "XDG_CONFIG_HOME": str(DATA_ROOT / ".config"),
        "XDG_STATE_HOME": str(DATA_ROOT / ".local/state"),
        "CUDA_CACHE_PATH": str(DATA_ROOT / ".cache/cuda"),
        "TORCH_HOME": str(DATA_ROOT / ".cache/torch"),
        "HF_HOME": str(DATA_ROOT / "models/huggingface"),
        "UV_CACHE_DIR": str(DATA_ROOT / ".uv-cache"),
        "OMNICLIENT_HUB_CACHE_DIR": str(DATA_ROOT / ".cache/ov/hub"),
    }


def ensure_storage():
    for value in storage_environment().values():
        Path(value).mkdir(parents=True, exist_ok=True)
    (DATA_ROOT / "datasets").mkdir(exist_ok=True)
    (DATA_ROOT / ".cache/kit").mkdir(parents=True, exist_ok=True)
