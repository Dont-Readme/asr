from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import time

from src.adapters.common import load_runtime_env
from src.adapters.qwen_align import LoadedAlignRuntime, align_with_runtime, load_align_runtime
from src.adapters.qwen_asr import LoadedAsrRuntime, load_asr_runtime, transcribe_with_runtime
from src.bootstrap import default_project_root
from src.config import AppConfig, load_config
from src.runtime.audio_preparation import prepare_runtime_audio
from src.utils.time import utcnow_iso
from src.api.upload_io import cleanup_temp_wave


@dataclass(slots=True)
class ResidentTranscriptionResult:
    asr: dict
    align: dict | None
    elapsed_sec: float


class ResidentTranscriptionRuntime:
    def __init__(self, *, project_root: Path | None = None) -> None:
        self.project_root = (project_root or default_project_root()).resolve()
        self.config: AppConfig = load_config(self.project_root)
        self.env = load_runtime_env(self.project_root)
        self.loaded_at = utcnow_iso()
        self.process_id = os.getpid()
        self.asr_runtime: LoadedAsrRuntime = load_asr_runtime(self.env)
        self._align_runtime: LoadedAlignRuntime | None = None

    def metadata(self) -> dict[str, object]:
        return {
            "status": "ready",
            "loaded_at": self.loaded_at,
            "process_id": self.process_id,
            "device": self.env.get("ASR_DEVICE", self.env.get("DEVICE", "")) or "cpu",
            "models": {
                "asr": self.asr_runtime.model_name,
                "align": self.align_runtime.model_name if self._align_runtime else self.env.get("ALIGN_MODEL", ""),
            },
        }

    @property
    def align_runtime(self) -> LoadedAlignRuntime:
        if self._align_runtime is None:
            self._align_runtime = load_align_runtime(self.env)
        return self._align_runtime

    def voice_transcribe(
        self,
        *,
        audio_path: Path,
        language: str | None = None,
        context: str | None = None,
    ) -> ResidentTranscriptionResult:
        started_at = time.perf_counter()
        prepared_path = prepare_runtime_audio(self.config, source_path=audio_path)
        try:
            asr_payload = transcribe_with_runtime(
                self.asr_runtime,
                audio_path=prepared_path,
                language=language,
                context=context,
            )
            return ResidentTranscriptionResult(
                asr=asr_payload,
                align=None,
                elapsed_sec=round(time.perf_counter() - started_at, 3),
            )
        finally:
            cleanup_temp_wave(prepared_path)

    def meeting_transcribe(
        self,
        *,
        audio_path: Path,
        language: str | None = None,
        context: str | None = None,
    ) -> ResidentTranscriptionResult:
        started_at = time.perf_counter()
        prepared_path = prepare_runtime_audio(self.config, source_path=audio_path)
        try:
            asr_payload = transcribe_with_runtime(
                self.asr_runtime,
                audio_path=prepared_path,
                language=language,
                context=context,
            )
            align_payload = align_with_runtime(
                self.align_runtime,
                audio_path=prepared_path,
                asr_payload=asr_payload,
                language=language,
            )
            return ResidentTranscriptionResult(
                asr=asr_payload,
                align=align_payload,
                elapsed_sec=round(time.perf_counter() - started_at, 3),
            )
        finally:
            cleanup_temp_wave(prepared_path)
