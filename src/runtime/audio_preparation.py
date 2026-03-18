from __future__ import annotations

from pathlib import Path

from src.api.upload_io import build_temp_wave_path, cleanup_temp_wave
from src.config import AppConfig
from src.utils.ffmpeg import convert_audio


def prepare_runtime_audio(config: AppConfig, *, source_path: Path) -> Path:
    prepared_path = build_temp_wave_path("runtime-audio")
    try:
        convert_audio(
            source_path,
            prepared_path,
            sample_rate=config.audio_target_sr,
            channels=config.audio_target_channels,
        )
    except Exception:
        cleanup_temp_wave(prepared_path)
        raise
    return prepared_path
