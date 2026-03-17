from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.config import AppConfig, load_config
from src.db.repo import SqliteJobRepository
from src.pipeline.job_context import JobContext
from src.utils.logging import setup_job_logger
from src.utils.paths import build_job_dirs, build_job_id, derive_meeting_title, ensure_project_roots


@dataclass(slots=True)
class JobRequest:
    source_path: Path
    meeting_title: str | None = None
    language: str = "ko"
    output_root: Path | None = None
    work_root: Path | None = None
    log_root: Path | None = None
    backchannel_mode: str | None = None
    pipeline_mode: str | None = None
    overwrite: bool = False


def default_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_app_config(
    request: JobRequest | None = None,
    *,
    project_root: Path | None = None,
) -> AppConfig:
    resolved_project_root = (project_root or default_project_root()).resolve()
    config = load_config(resolved_project_root)
    if request is None:
        return config
    return config.with_overrides(
        pipeline_mode=request.pipeline_mode,
        work_root=request.work_root.resolve() if request.work_root else None,
        output_root=request.output_root.resolve() if request.output_root else None,
        log_root=request.log_root.resolve() if request.log_root else None,
        backchannel_mode=request.backchannel_mode,
    )


def create_job_context(request: JobRequest, *, project_root: Path | None = None) -> JobContext:
    resolved_project_root = (project_root or default_project_root()).resolve()
    config = load_app_config(request, project_root=resolved_project_root)
    ensure_project_roots(config)

    input_path = request.source_path.expanduser().resolve()
    meeting_title = derive_meeting_title(input_path, request.meeting_title)
    job_id = build_job_id(meeting_title, overwrite=request.overwrite)
    work_dir, output_dir, log_path = build_job_dirs(config, job_id)
    logger = setup_job_logger(job_id, log_path)
    repo = SqliteJobRepository(config.db_url, resolved_project_root)

    context = JobContext(
        job_id=job_id,
        input_path=input_path,
        meeting_title=meeting_title,
        language=request.language,
        config=config,
        work_dir=work_dir,
        output_dir=output_dir,
        log_path=log_path,
        logger=logger,
        repo=repo,
        backchannel_mode=config.backchannel_mode,
        overwrite=request.overwrite,
    )
    repo.create_job(
        job_id=job_id,
        input_path=input_path,
        meeting_title=meeting_title,
        language=request.language,
        work_dir=work_dir,
        output_dir=output_dir,
        log_path=log_path,
    )
    return context

__all__ = ["JobRequest", "create_job_context", "default_project_root", "load_app_config"]
