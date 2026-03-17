from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException

from src.api.models import AudioFeatureRequest, JobCreatedResponse, JobStatusResponse, SummaryFeatureRequest
from src.bootstrap import JobRequest, create_job_context, default_project_root, load_app_config
from src.db.repo import SqliteJobRepository
from src.services.diarization import run_diarization
from src.services.pipeline import run_pipeline_job
from src.services.summarization import run_summary
from src.services.transcription import run_transcription
from src.utils.errors import PipelineError


def create_app() -> FastAPI:
    app = FastAPI(title="ASR Meeting Pipeline API", version="0.1.0")

    @app.post("/transcriptions", response_model=JobCreatedResponse)
    def create_transcription(request: AudioFeatureRequest) -> JobCreatedResponse:
        context = create_job_context(_audio_job_request(request))
        try:
            result = run_transcription(context)
        except PipelineError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return JobCreatedResponse(
            job_id=context.job_id,
            meeting_title=context.meeting_title,
            artifacts={
                "audio_path": str(result.preprocessed_audio_path),
                "asr_json_path": str(result.asr_json_path),
                "align_json_path": str(result.align_json_path),
            },
        )

    @app.post("/diarizations", response_model=JobCreatedResponse)
    def create_diarization(request: AudioFeatureRequest) -> JobCreatedResponse:
        context = create_job_context(_audio_job_request(request))
        try:
            result = run_diarization(context)
        except PipelineError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return JobCreatedResponse(
            job_id=context.job_id,
            meeting_title=context.meeting_title,
            artifacts={
                "audio_path": str(result.preprocessed_audio_path),
                "diarization_json_path": str(result.diarization_json_path),
                "diarization_rttm_path": str(result.diarization_rttm_path),
            },
        )

    @app.post("/summaries", response_model=JobCreatedResponse)
    def create_summary(request: SummaryFeatureRequest) -> JobCreatedResponse:
        context = create_job_context(_summary_job_request(request))
        try:
            result = run_summary(context, transcript_path=Path(request.transcript_path))
        except PipelineError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return JobCreatedResponse(
            job_id=context.job_id,
            meeting_title=context.meeting_title,
            artifacts={
                "transcript_json_path": str(result.transcript_json_path),
                "summary_json_path": str(result.summary_json_path),
            },
        )

    @app.post("/pipelines", response_model=JobCreatedResponse)
    def create_pipeline(request: AudioFeatureRequest) -> JobCreatedResponse:
        context = create_job_context(_audio_job_request(request))
        try:
            result = run_pipeline_job(context)
        except PipelineError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return JobCreatedResponse(
            job_id=context.job_id,
            meeting_title=context.meeting_title,
            artifacts=result,
        )

    @app.get("/jobs/{job_id}", response_model=JobStatusResponse)
    def get_job(job_id: str) -> JobStatusResponse:
        project_root = default_project_root()
        config = load_app_config(project_root=project_root)
        repo = SqliteJobRepository(config.db_url, project_root)
        job = repo.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="job not found")
        return JobStatusResponse(job=job, artifacts=repo.list_artifacts(job_id))

    return app


def _audio_job_request(request: AudioFeatureRequest) -> JobRequest:
    return JobRequest(
        source_path=Path(request.audio_path),
        meeting_title=request.meeting_title,
        language=request.language,
        output_root=Path(request.output_root).resolve() if request.output_root else None,
        work_root=Path(request.work_root).resolve() if request.work_root else None,
        log_root=Path(request.log_root).resolve() if request.log_root else None,
        pipeline_mode=request.pipeline_mode,
        overwrite=request.overwrite,
    )


def _summary_job_request(request: SummaryFeatureRequest) -> JobRequest:
    return JobRequest(
        source_path=Path(request.transcript_path),
        meeting_title=request.meeting_title,
        language=request.language,
        output_root=Path(request.output_root).resolve() if request.output_root else None,
        work_root=Path(request.work_root).resolve() if request.work_root else None,
        log_root=Path(request.log_root).resolve() if request.log_root else None,
        pipeline_mode=request.pipeline_mode,
        overwrite=request.overwrite,
    )
