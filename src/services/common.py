from __future__ import annotations

from pathlib import Path

from src.db.models import JobStage, JobStatus
from src.pipeline.job_context import JobContext
from src.stages import preprocess
from src.utils.errors import StageError


def ensure_preprocessed_audio(context: JobContext) -> Path:
    if context.preprocessed_audio_path.exists():
        return context.preprocessed_audio_path
    return preprocess.run(context)


def run_feature_stage(context: JobContext, stage: JobStage, runner):
    context.repo.update_job_status(
        context.job_id,
        status=JobStatus.RUNNING,
        current_stage=stage,
    )
    context.logger.info("%s started.", stage.value)
    result = runner(context)
    context.logger.info("%s completed.", stage.value)
    return result


def mark_feature_done(context: JobContext, stage: JobStage) -> None:
    context.repo.update_job_status(
        context.job_id,
        status=JobStatus.DONE,
        current_stage=stage,
    )


def mark_feature_failed(context: JobContext, stage: str, error: Exception) -> None:
    resolved_stage = error.stage if isinstance(error, StageError) else stage
    message = error.message if isinstance(error, StageError) else str(error)
    context.logger.exception("Feature failed at %s", resolved_stage)
    context.repo.update_job_status(
        context.job_id,
        status=JobStatus.FAILED,
        current_stage=None,
        error_stage=resolved_stage,
        error_message=message,
    )
