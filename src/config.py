from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import os


def _strip_inline_comment(raw_value: str) -> str:
    in_single = False
    in_double = False
    for index, char in enumerate(raw_value):
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            return raw_value[:index].strip()
    return raw_value.strip()


def load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, raw_value = stripped.split("=", 1)
        value = _strip_inline_comment(raw_value)
        if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
            value = value[1:-1]
        values[key.strip()] = value
    return values


def _get_setting(raw_values: dict[str, str], key: str, default: str) -> str:
    return os.environ.get(key, raw_values.get(key, default))


def _resolve_path(project_root: Path, raw_value: str) -> Path:
    path = Path(raw_value)
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def _to_bool(raw_value: str) -> bool:
    return raw_value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class AppConfig:
    project_root: Path
    pipeline_mode: str
    work_root: Path
    output_root: Path
    log_root: Path
    input_root: Path
    device: str
    asr_model: str
    align_model: str
    diarization_model: str
    asr_command: str
    align_command: str
    diarization_command: str
    hf_home: Path
    huggingface_hub_token: str
    db_url: str
    summary_provider: str
    summary_base_url: str
    summary_endpoint_path: str
    summary_api_key: str
    summary_temperature: float
    summary_top_p: float
    summary_max_tokens: int
    summary_response_key: str
    summary_model: str
    audio_target_sr: int
    audio_target_channels: int
    merge_ambiguous_sec: float
    merge_ambiguous_ratio: float
    backchannel_mode: str
    transcribe_api_base_url: str = "http://127.0.0.1:8091"
    diarize_api_base_url: str = "http://127.0.0.1:8092"
    summarize_api_base_url: str = "http://127.0.0.1:8093"

    def with_overrides(
        self,
        *,
        pipeline_mode: str | None = None,
        work_root: Path | None = None,
        output_root: Path | None = None,
        log_root: Path | None = None,
        backchannel_mode: str | None = None,
    ) -> "AppConfig":
        updated = replace(
            self,
            pipeline_mode=pipeline_mode or self.pipeline_mode,
            work_root=work_root or self.work_root,
            output_root=output_root or self.output_root,
            log_root=log_root or self.log_root,
            backchannel_mode=backchannel_mode or self.backchannel_mode,
        )
        if updated.pipeline_mode == "mock":
            updated = replace(updated, summary_provider="mock")
        return updated


def load_config(project_root: Path, env_path: Path | None = None) -> AppConfig:
    env_file = env_path or project_root / ".env"
    raw_values = load_env_file(env_file)

    return AppConfig(
        project_root=project_root.resolve(),
        pipeline_mode=_get_setting(raw_values, "PIPELINE_MODE", "production"),
        work_root=_resolve_path(project_root, _get_setting(raw_values, "WORK_ROOT", "./work")),
        output_root=_resolve_path(project_root, _get_setting(raw_values, "OUTPUT_ROOT", "./output")),
        log_root=_resolve_path(project_root, _get_setting(raw_values, "LOG_ROOT", "./logs")),
        input_root=_resolve_path(project_root, _get_setting(raw_values, "INPUT_ROOT", "./input")),
        device=_get_setting(raw_values, "DEVICE", "cuda"),
        asr_model=_get_setting(raw_values, "ASR_MODEL", "Qwen/Qwen3-ASR-1.7B"),
        align_model=_get_setting(raw_values, "ALIGN_MODEL", "Qwen/Qwen3-ForcedAligner-0.6B"),
        diarization_model=_get_setting(
            raw_values,
            "DIARIZATION_MODEL",
            "pyannote/speaker-diarization-community-1",
        ),
        asr_command=_get_setting(raw_values, "ASR_COMMAND", ""),
        align_command=_get_setting(raw_values, "ALIGN_COMMAND", ""),
        diarization_command=_get_setting(raw_values, "DIARIZATION_COMMAND", ""),
        hf_home=_resolve_path(project_root, _get_setting(raw_values, "HF_HOME", "./.hf_cache")),
        huggingface_hub_token=_get_setting(raw_values, "HUGGINGFACE_HUB_TOKEN", ""),
        db_url=_get_setting(raw_values, "DB_URL", "sqlite:///./work/app.sqlite3"),
        summary_provider=_get_setting(raw_values, "SUMMARY_PROVIDER", "vllm_generate"),
        summary_base_url=_get_setting(raw_values, "SUMMARY_BASE_URL", "http://127.0.0.1:8000"),
        summary_endpoint_path=_get_setting(raw_values, "SUMMARY_ENDPOINT_PATH", "/generate"),
        summary_api_key=_get_setting(raw_values, "SUMMARY_API_KEY", ""),
        summary_temperature=float(_get_setting(raw_values, "SUMMARY_TEMPERATURE", "0.3")),
        summary_top_p=float(_get_setting(raw_values, "SUMMARY_TOP_P", "0.9")),
        summary_max_tokens=int(_get_setting(raw_values, "SUMMARY_MAX_TOKENS", "1000")),
        summary_response_key=_get_setting(raw_values, "SUMMARY_RESPONSE_KEY", "generated_text"),
        summary_model=_get_setting(raw_values, "SUMMARY_MODEL", ""),
        transcribe_api_base_url=_get_setting(raw_values, "TRANSCRIBE_API_BASE_URL", "http://127.0.0.1:8091"),
        diarize_api_base_url=_get_setting(raw_values, "DIARIZE_API_BASE_URL", "http://127.0.0.1:8092"),
        summarize_api_base_url=_get_setting(raw_values, "SUMMARIZE_API_BASE_URL", "http://127.0.0.1:8093"),
        audio_target_sr=int(_get_setting(raw_values, "AUDIO_TARGET_SR", "16000")),
        audio_target_channels=int(_get_setting(raw_values, "AUDIO_TARGET_CHANNELS", "1")),
        merge_ambiguous_sec=float(_get_setting(raw_values, "MERGE_AMBIGUOUS_SEC", "0.08")),
        merge_ambiguous_ratio=float(_get_setting(raw_values, "MERGE_AMBIGUOUS_RATIO", "0.2")),
        backchannel_mode=_get_setting(raw_values, "BACKCHANNEL_MODE", "keep"),
    )


__all__ = ["AppConfig", "load_config", "load_env_file", "_to_bool"]
