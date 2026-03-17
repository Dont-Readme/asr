from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException

from src.api.models import RuntimeHealthResponse, TranscriptionRuntimeRequest, TranscriptionRuntimeResponse
from src.runtime.transcription_runtime import ResidentTranscriptionRuntime
from src.utils.errors import PipelineError


def create_app() -> FastAPI:
    runtime = ResidentTranscriptionRuntime()
    app = FastAPI(title="ASR Transcription Runtime API", version="0.1.0")
    app.state.runtime = runtime

    @app.get("/health", response_model=RuntimeHealthResponse)
    def health() -> RuntimeHealthResponse:
        return RuntimeHealthResponse(**runtime.metadata())

    @app.post("/transcribe", response_model=TranscriptionRuntimeResponse)
    def transcribe(request: TranscriptionRuntimeRequest) -> TranscriptionRuntimeResponse:
        try:
            result = runtime.transcribe(
                audio_path=Path(request.audio_path).expanduser().resolve(),
                language=request.language,
                context=request.context,
            )
        except (PipelineError, RuntimeError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return TranscriptionRuntimeResponse(
            asr=result.asr,
            align=result.align,
            elapsed_sec=result.elapsed_sec,
        )

    return app
