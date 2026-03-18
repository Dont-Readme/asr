from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import time

from src.adapters.common import load_runtime_env
from src.adapters.pyannote_diarize import LoadedDiarizationRuntime, diarize_with_runtime, load_diarization_runtime
from src.bootstrap import default_project_root
from src.config import AppConfig, load_config
from src.runtime.audio_preparation import prepare_runtime_audio
from src.utils.time import utcnow_iso
from src.api.upload_io import cleanup_temp_wave


@dataclass(slots=True)
class ResidentDiarizationResult:
    diarization: dict
    rttm: str
    elapsed_sec: float


class ResidentDiarizationRuntime:
    def __init__(self, *, project_root: Path | None = None) -> None:
        self.project_root = (project_root or default_project_root()).resolve()
        self.config: AppConfig = load_config(self.project_root)
        self.env = load_runtime_env(self.project_root)
        self.loaded_at = utcnow_iso()
        self.process_id = os.getpid()
        self.runtime: LoadedDiarizationRuntime = load_diarization_runtime(self.env)

    def metadata(self) -> dict[str, object]:
        return {
            "status": "ready",
            "loaded_at": self.loaded_at,
            "process_id": self.process_id,
            "device": self.env.get("DIARIZATION_DEVICE", self.env.get("DEVICE", "")) or "cpu",
            "models": {
                "diarization": self.runtime.model_name,
            },
        }

    def diarize(
        self,
        *,
        audio_path: Path,
        num_speakers: int | None = None,
        min_speakers: int | None = None,
        max_speakers: int | None = None,
    ) -> ResidentDiarizationResult:
        started_at = time.perf_counter()
        prepared_path = prepare_runtime_audio(self.config, source_path=audio_path)
        try:
            payload, rttm = diarize_with_runtime(
                self.runtime,
                audio_path=prepared_path,
                num_speakers=num_speakers,
                min_speakers=min_speakers,
                max_speakers=max_speakers,
            )
            return ResidentDiarizationResult(
                diarization=payload,
                rttm=rttm,
                elapsed_sec=round(time.perf_counter() - started_at, 3),
            )
        finally:
            cleanup_temp_wave(prepared_path)
