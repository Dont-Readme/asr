from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from src.api.models import JobAcceptedResponse, JobStatusResponse, MeetingNotePathRequest
from src.api.upload_io import save_upload_to_input_root
from src.bootstrap import default_project_root, load_app_config
from src.db.repo import SqliteJobRepository
from src.services.meeting_note_jobs import MeetingNoteJobService


def create_app(job_service: MeetingNoteJobService | None = None) -> FastAPI:
    project_root = default_project_root()
    config = load_app_config(project_root=project_root)
    resolved_job_service = job_service or MeetingNoteJobService(project_root=project_root)

    app = FastAPI(title="ASR Meeting Orchestration API", version="0.2.0")
    app.state.job_service = resolved_job_service

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ready"}

    @app.post("/meeting-note-jobs/by-path", response_model=JobAcceptedResponse)
    def create_meeting_note_job_by_path(request: MeetingNotePathRequest) -> JobAcceptedResponse:
        submitted = resolved_job_service.submit_path_job(
            audio_path=Path(request.audio_path).expanduser().resolve(),
            meeting_title=request.meeting_title,
            language=request.language,
            output_root=Path(request.output_root).resolve() if request.output_root else None,
            work_root=Path(request.work_root).resolve() if request.work_root else None,
            log_root=Path(request.log_root).resolve() if request.log_root else None,
            pipeline_mode=request.pipeline_mode,
            overwrite=request.overwrite,
        )
        return JobAcceptedResponse(
            job_id=submitted.job_id,
            meeting_title=submitted.meeting_title,
            status="PENDING",
            status_url=f"/meeting-note-jobs/{submitted.job_id}",
        )

    @app.post("/meeting-note-jobs/upload", response_model=JobAcceptedResponse)
    def create_meeting_note_job_upload(
        file: UploadFile = File(...),
        meeting_title: str | None = Form(default=None),
        language: str = Form(default="ko"),
        output_root: str | None = Form(default=None),
        work_root: str | None = Form(default=None),
        log_root: str | None = Form(default=None),
        pipeline_mode: str | None = Form(default=None),
        overwrite: bool = Form(default=False),
    ) -> JobAcceptedResponse:
        stored_path = save_upload_to_input_root(config.input_root, file, prefix="meeting-note")
        submitted = resolved_job_service.submit_path_job(
            audio_path=stored_path,
            meeting_title=meeting_title,
            language=language,
            output_root=Path(output_root).resolve() if output_root else None,
            work_root=Path(work_root).resolve() if work_root else None,
            log_root=Path(log_root).resolve() if log_root else None,
            pipeline_mode=pipeline_mode,
            overwrite=overwrite,
        )
        return JobAcceptedResponse(
            job_id=submitted.job_id,
            meeting_title=submitted.meeting_title,
            status="PENDING",
            status_url=f"/meeting-note-jobs/{submitted.job_id}",
        )

    @app.get("/meeting-note-jobs/{job_id}", response_model=JobStatusResponse)
    @app.get("/jobs/{job_id}", response_model=JobStatusResponse)
    def get_job(job_id: str) -> JobStatusResponse:
        repo = SqliteJobRepository(config.db_url, project_root)
        job = repo.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="job not found")
        return JobStatusResponse(job=job, artifacts=repo.list_artifacts(job_id))

    return app
