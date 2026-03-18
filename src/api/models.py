from __future__ import annotations

from pydantic import BaseModel, Field


class BaseJobRequestModel(BaseModel):
    meeting_title: str | None = Field(default=None)
    language: str = Field(default="ko")
    output_root: str | None = Field(default=None)
    work_root: str | None = Field(default=None)
    log_root: str | None = Field(default=None)
    pipeline_mode: str | None = Field(default=None)
    overwrite: bool = Field(default=False)


class JobAcceptedResponse(BaseModel):
    job_id: str
    meeting_title: str
    status: str
    status_url: str


class JobStatusResponse(BaseModel):
    job: dict
    artifacts: list[dict]


class RuntimeHealthResponse(BaseModel):
    status: str
    loaded_at: str
    process_id: int
    device: str
    models: dict[str, str]


class VoiceTranscriptionPathRequest(BaseModel):
    audio_path: str
    language: str | None = Field(default=None)
    context: str | None = Field(default=None)


class MeetingTranscriptionPathRequest(VoiceTranscriptionPathRequest):
    pass


class VoiceTranscriptionResponse(BaseModel):
    text: str
    asr: dict
    elapsed_sec: float


class MeetingTranscriptionResponse(BaseModel):
    text: str
    asr: dict
    align: dict
    elapsed_sec: float


class DiarizationPathRequest(BaseModel):
    audio_path: str
    num_speakers: int | None = Field(default=None)
    min_speakers: int | None = Field(default=None)
    max_speakers: int | None = Field(default=None)


class DiarizationRuntimeResponse(BaseModel):
    diarization: dict
    rttm: str
    elapsed_sec: float


class SummaryPayloadRequest(BaseModel):
    meeting_title: str
    transcript: dict


class SummaryPayloadResponse(BaseModel):
    summary: dict
    elapsed_sec: float


class MeetingNotePathRequest(BaseJobRequestModel):
    audio_path: str
