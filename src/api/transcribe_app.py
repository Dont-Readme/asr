from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from src.api.models import (
    MeetingTranscriptionPathRequest,
    MeetingTranscriptionResponse,
    RuntimeHealthResponse,
    VoiceTranscriptionPathRequest,
    VoiceTranscriptionResponse,
)
from src.api.upload_io import delete_file_quietly, save_upload_to_temp
from src.runtime.transcription_runtime import ResidentTranscriptionResult, ResidentTranscriptionRuntime
from src.services.task_runner import QueueBusyError, QueueWaitTimeoutError, TaskRunner
from src.utils.errors import PipelineError


VOICE_PRIORITY = 10
MEETING_PRIORITY = 100


def create_app(
    runtime: ResidentTranscriptionRuntime | None = None,
    task_runner: TaskRunner | None = None,
) -> FastAPI:
    resolved_runtime = runtime or ResidentTranscriptionRuntime()
    runtime_config = getattr(resolved_runtime, "config", None)
    resolved_runner = task_runner or TaskRunner(
        name="transcribe",
        workers=getattr(runtime_config, "transcribe_max_concurrency", 1),
    )
    app = FastAPI(title="ASR Transcription Runtime API", version="0.2.0")
    app.state.runtime = resolved_runtime
    app.state.task_runner = resolved_runner

    @app.get("/health", response_model=RuntimeHealthResponse)
    def health() -> RuntimeHealthResponse:
        return RuntimeHealthResponse(**resolved_runtime.metadata())

    @app.post("/voice-transcriptions/by-path", response_model=VoiceTranscriptionResponse)
    def voice_transcribe_by_path(request: VoiceTranscriptionPathRequest) -> VoiceTranscriptionResponse:
        try:
            result = resolved_runner.submit(
                lambda: resolved_runtime.voice_transcribe(
                    audio_path=Path(request.audio_path).expanduser().resolve(),
                    language=request.language,
                    context=request.context,
                ),
                priority=VOICE_PRIORITY,
                max_pending=getattr(runtime_config, "voice_max_pending", 3),
                wait_timeout_sec=getattr(runtime_config, "voice_wait_timeout_sec", 15.0),
            )
        except (PipelineError, RuntimeError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except (QueueBusyError, QueueWaitTimeoutError) as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        return _build_voice_response(result)

    @app.post("/voice-transcriptions/upload", response_model=VoiceTranscriptionResponse)
    def voice_transcribe_upload(
        file: UploadFile = File(...),
        language: str | None = Form(default=None),
        context: str | None = Form(default=None),
    ) -> VoiceTranscriptionResponse:
        stored_path = save_upload_to_temp(resolved_runtime.project_root, file, prefix="voice")
        try:
            result = resolved_runner.submit(
                lambda: resolved_runtime.voice_transcribe(
                    audio_path=stored_path,
                    language=language,
                    context=context,
                ),
                priority=VOICE_PRIORITY,
                max_pending=getattr(runtime_config, "voice_max_pending", 3),
                wait_timeout_sec=getattr(runtime_config, "voice_wait_timeout_sec", 15.0),
            )
        except (PipelineError, RuntimeError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except (QueueBusyError, QueueWaitTimeoutError) as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        finally:
            delete_file_quietly(stored_path)
        return _build_voice_response(result)

    @app.post("/meeting-transcriptions/by-path", response_model=MeetingTranscriptionResponse)
    def meeting_transcribe_by_path(request: MeetingTranscriptionPathRequest) -> MeetingTranscriptionResponse:
        try:
            result = resolved_runner.submit(
                lambda: resolved_runtime.meeting_transcribe(
                    audio_path=Path(request.audio_path).expanduser().resolve(),
                    language=request.language,
                    context=request.context,
                ),
                priority=MEETING_PRIORITY,
                max_pending=getattr(runtime_config, "meeting_transcribe_max_pending", 10),
            )
        except (PipelineError, RuntimeError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except (QueueBusyError, QueueWaitTimeoutError) as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        return _build_meeting_response(result)

    @app.post("/meeting-transcriptions/upload", response_model=MeetingTranscriptionResponse)
    def meeting_transcribe_upload(
        file: UploadFile = File(...),
        language: str | None = Form(default=None),
        context: str | None = Form(default=None),
    ) -> MeetingTranscriptionResponse:
        stored_path = save_upload_to_temp(resolved_runtime.project_root, file, prefix="meeting")
        try:
            result = resolved_runner.submit(
                lambda: resolved_runtime.meeting_transcribe(
                    audio_path=stored_path,
                    language=language,
                    context=context,
                ),
                priority=MEETING_PRIORITY,
                max_pending=getattr(runtime_config, "meeting_transcribe_max_pending", 10),
            )
        except (PipelineError, RuntimeError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except (QueueBusyError, QueueWaitTimeoutError) as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        finally:
            delete_file_quietly(stored_path)
        return _build_meeting_response(result)

    return app


def _build_voice_response(result: ResidentTranscriptionResult) -> VoiceTranscriptionResponse:
    return VoiceTranscriptionResponse(
        text=_join_segment_texts(result.asr.get("segments", [])),
        asr=result.asr,
        elapsed_sec=result.elapsed_sec,
    )


def _build_meeting_response(result: ResidentTranscriptionResult) -> MeetingTranscriptionResponse:
    align_payload = result.align or {"segments": []}
    return MeetingTranscriptionResponse(
        text=_join_segment_texts(align_payload.get("segments", []) or result.asr.get("segments", [])),
        asr=result.asr,
        align=align_payload,
        elapsed_sec=result.elapsed_sec,
    )


def _join_segment_texts(segments: list[dict]) -> str:
    return " ".join(str(segment.get("text", "")).strip() for segment in segments if str(segment.get("text", "")).strip())
