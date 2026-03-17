from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException

from src.api.models import DiarizationRuntimeRequest, DiarizationRuntimeResponse, RuntimeHealthResponse
from src.runtime.diarization_runtime import ResidentDiarizationRuntime
from src.utils.errors import PipelineError


def create_app() -> FastAPI:
    runtime = ResidentDiarizationRuntime()
    app = FastAPI(title="ASR Diarization Runtime API", version="0.1.0")
    app.state.runtime = runtime

    @app.get("/health", response_model=RuntimeHealthResponse)
    def health() -> RuntimeHealthResponse:
        return RuntimeHealthResponse(**runtime.metadata())

    @app.post("/diarize", response_model=DiarizationRuntimeResponse)
    def diarize(request: DiarizationRuntimeRequest) -> DiarizationRuntimeResponse:
        try:
            result = runtime.diarize(
                audio_path=Path(request.audio_path).expanduser().resolve(),
                num_speakers=request.num_speakers,
                min_speakers=request.min_speakers,
                max_speakers=request.max_speakers,
            )
        except (PipelineError, RuntimeError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return DiarizationRuntimeResponse(
            diarization=result.diarization,
            rttm=result.rttm,
            elapsed_sec=result.elapsed_sec,
        )

    return app
