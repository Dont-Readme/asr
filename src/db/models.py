from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    DONE = "DONE"


class JobStage(str, Enum):
    PREPROCESS = "PREPROCESS"
    ASR = "ASR"
    ALIGN = "ALIGN"
    DIARIZE = "DIARIZE"
    MERGE = "MERGE"
    SUMMARIZE = "SUMMARIZE"
    EXPORT = "EXPORT"


@dataclass(slots=True)
class TranscriptSegmentRecord:
    speaker_label: str
    start_ms: int
    end_ms: int
    text: str
    words_json: str
