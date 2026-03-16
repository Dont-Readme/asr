from __future__ import annotations

import json
import os
from pathlib import Path
import wave

from src.config import load_env_file


def project_root_from(module_path: Path) -> Path:
    return module_path.resolve().parents[2]


def load_runtime_env(project_root: Path) -> dict[str, str]:
    env_values = load_env_file(project_root / ".env")
    merged = {**env_values, **os.environ}

    hf_home = merged.get("HF_HOME", "").strip()
    if hf_home:
        hf_home_path = Path(hf_home)
        if not hf_home_path.is_absolute():
            hf_home_path = project_root / hf_home_path
        os.environ.setdefault("HF_HOME", str(hf_home_path.resolve()))

    token = merged.get("HUGGINGFACE_HUB_TOKEN", "").strip()
    if token:
        os.environ.setdefault("HUGGINGFACE_HUB_TOKEN", token)
        os.environ.setdefault("HF_TOKEN", token)

    return merged


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def audio_duration_seconds(audio_path: Path) -> float:
    with wave.open(str(audio_path), "rb") as wav_file:
        frame_count = wav_file.getnframes()
        sample_rate = wav_file.getframerate()
    if sample_rate <= 0:
        return 0.0
    return round(frame_count / float(sample_rate), 3)


def chunked(items: list, size: int) -> list[list]:
    if size <= 0:
        return [items]
    return [items[index : index + size] for index in range(0, len(items), size)]


def unique_csv(values: list[str]) -> str:
    ordered: list[str] = []
    for value in values:
        candidate = value.strip()
        if candidate and candidate not in ordered:
            ordered.append(candidate)
    return ",".join(ordered)


def normalize_language_name(raw_language: str | None) -> str:
    if raw_language is None:
        return ""
    value = str(raw_language).strip()
    if not value:
        return ""
    if "," in value:
        value = value.split(",", 1)[0].strip()
    mapping = {
        "ko": "Korean",
        "en": "English",
        "ja": "Japanese",
        "zh": "Chinese",
        "yue": "Cantonese",
    }
    if value.lower() in mapping:
        return mapping[value.lower()]
    return value[:1].upper() + value[1:].lower()


def env_optional_int(env: dict[str, str], key: str) -> int | None:
    raw_value = env.get(key, "").strip()
    if not raw_value:
        return None
    return int(raw_value)


def torch_dtype_from_name(torch_module, raw_dtype: str | None):
    if raw_dtype is None or not raw_dtype.strip():
        return None
    name = raw_dtype.strip().lower()
    if name == "auto":
        return None
    mapping = {
        "float16": torch_module.float16,
        "fp16": torch_module.float16,
        "bfloat16": torch_module.bfloat16,
        "bf16": torch_module.bfloat16,
        "float32": torch_module.float32,
        "fp32": torch_module.float32,
    }
    if name not in mapping:
        raise ValueError(f"Unsupported dtype: {raw_dtype}")
    return mapping[name]


def load_kwargs_from_env(torch_module, env: dict[str, str], prefix: str) -> dict:
    kwargs: dict[str, object] = {}
    dtype = torch_dtype_from_name(torch_module, env.get(f"{prefix}_DTYPE"))
    if dtype is not None:
        kwargs["dtype"] = dtype

    device_map = env.get(f"{prefix}_DEVICE_MAP", "").strip()
    if device_map:
        kwargs["device_map"] = device_map

    attn_implementation = env.get(f"{prefix}_ATTN_IMPLEMENTATION", "").strip()
    if attn_implementation:
        kwargs["attn_implementation"] = attn_implementation

    return kwargs


def move_model_to_device(model, torch_module, device_name: str | None) -> None:
    if not device_name or not str(device_name).strip():
        return
    if device_name == "auto":
        return
    if str(device_name).startswith("cuda") and not torch_module.cuda.is_available():
        raise RuntimeError("CUDA device was requested but torch.cuda.is_available() is False.")
    model.to(torch_module.device(device_name))
