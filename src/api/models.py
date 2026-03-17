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


class AudioFeatureRequest(BaseJobRequestModel):
    audio_path: str


class SummaryFeatureRequest(BaseJobRequestModel):
    transcript_path: str
    meeting_title: str


class JobCreatedResponse(BaseModel):
    job_id: str
    meeting_title: str
    artifacts: dict[str, str]


class JobStatusResponse(BaseModel):
    job: dict
    artifacts: list[dict]

