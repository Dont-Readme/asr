from __future__ import annotations

from dataclasses import dataclass, field
from logging import Logger
from pathlib import Path

from src.config import AppConfig
from src.db.repo import SqliteJobRepository


@dataclass(slots=True)
class JobContext:
    job_id: str
    input_path: Path
    meeting_title: str
    language: str
    config: AppConfig
    work_dir: Path
    output_dir: Path
    log_path: Path
    logger: Logger
    repo: SqliteJobRepository
    backchannel_mode: str
    overwrite: bool = False
    artifacts: dict[str, Path] = field(default_factory=dict)

    @property
    def preprocessed_audio_path(self) -> Path:
        return self.work_dir / "audio_16k_mono.wav"

    @property
    def asr_json_path(self) -> Path:
        return self.work_dir / "asr.json"

    @property
    def align_json_path(self) -> Path:
        return self.work_dir / "align.json"

    @property
    def diarization_json_path(self) -> Path:
        return self.work_dir / "diarization.json"

    @property
    def diarization_rttm_path(self) -> Path:
        return self.work_dir / "diarization.rttm"

    @property
    def transcript_json_path(self) -> Path:
        return self.output_dir / "transcript_diarized.json"

    @property
    def summary_json_path(self) -> Path:
        return self.output_dir / "summary.json"

    @property
    def meeting_notes_path(self) -> Path:
        return self.output_dir / "meeting_notes.txt"
