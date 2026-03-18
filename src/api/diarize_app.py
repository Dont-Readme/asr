from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from src.api.models import DiarizationPathRequest, DiarizationRuntimeResponse, RuntimeHealthResponse
from src.api.upload_io import delete_file_quietly, save_upload_to_temp
from src.runtime.diarization_runtime import ResidentDiarizationRuntime
from src.utils.errors import PipelineError


def create_app(runtime: ResidentDiarizationRuntime | None = None) -> FastAPI:
    resolved_runtime = runtime or ResidentDiarizationRuntime()
    app = FastAPI(title="ASR Diarization Runtime API", version="0.2.0")
    app.state.runtime = resolved_runtime

    @app.get("/health", response_model=RuntimeHealthResponse)
    def health() -> RuntimeHealthResponse:
        return RuntimeHealthResponse(**resolved_runtime.metadata())

    @app.post("/diarizations/by-path", response_model=DiarizationRuntimeResponse)
    def diarize_by_path(request: DiarizationPathRequest) -> DiarizationRuntimeResponse:
        try:
            result = resolved_runtime.diarize(
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

    @app.post("/diarizations/upload", response_model=DiarizationRuntimeResponse)
    def diarize_upload(
        file: UploadFile = File(...),
        num_speakers: int | None = Form(default=None),
        min_speakers: int | None = Form(default=None),
        max_speakers: int | None = Form(default=None),
    ) -> DiarizationRuntimeResponse:
        stored_path = save_upload_to_temp(resolved_runtime.project_root, file, prefix="diarize")
        try:
            result = resolved_runtime.diarize(
                audio_path=stored_path,
                num_speakers=num_speakers,
                min_speakers=min_speakers,
                max_speakers=max_speakers,
            )
        except (PipelineError, RuntimeError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        finally:
            delete_file_quietly(stored_path)
        return DiarizationRuntimeResponse(
            diarization=result.diarization,
            rttm=result.rttm,
            elapsed_sec=result.elapsed_sec,
        )

    return app
