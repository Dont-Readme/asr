from __future__ import annotations

from src.db.models import JobStage, JobStatus
from src.pipeline.job_context import JobContext
from src.services.persistence import persist_summary_result, persist_transcript_records
from src.stages import align, asr, diarize, export, merge, preprocess, summarize
from src.utils.errors import StageError


def run_pipeline(context: JobContext) -> dict[str, str]:
    context.repo.update_job_status(context.job_id, status=JobStatus.RUNNING)

    try:
        _run_stage(context, JobStage.PREPROCESS, preprocess.run)
        _run_stage(context, JobStage.ASR, asr.run)
        _run_stage(context, JobStage.ALIGN, align.run)
        _run_stage(context, JobStage.DIARIZE, diarize.run)

        transcript_result = _run_stage(context, JobStage.MERGE, merge.run)
        persist_transcript_records(context, transcript_result)

        summary_result = _run_stage(context, JobStage.SUMMARIZE, summarize.run)
        persist_summary_result(context, summary_result)

        notes_path = _run_stage(context, JobStage.EXPORT, export.run)
        context.repo.update_job_status(
            context.job_id,
            status=JobStatus.DONE,
            current_stage=JobStage.EXPORT,
        )
        return {
            "job_id": context.job_id,
            "transcript_path": str(context.transcript_json_path),
            "summary_path": str(context.summary_json_path),
            "meeting_notes_path": str(notes_path),
        }
    except StageError as error:
        context.logger.exception("Pipeline failed at %s", error.stage)
        context.repo.update_job_status(
            context.job_id,
            status=JobStatus.FAILED,
            current_stage=None,
            error_stage=error.stage,
            error_message=error.message,
        )
        raise
    except Exception as error:  # pragma: no cover - safety net
        context.logger.exception("Unexpected pipeline failure")
        context.repo.update_job_status(
            context.job_id,
            status=JobStatus.FAILED,
            current_stage=None,
            error_stage="UNKNOWN",
            error_message=str(error),
        )
        raise


def _run_stage(context: JobContext, stage: JobStage, runner):
    context.repo.update_job_status(
        context.job_id,
        status=JobStatus.RUNNING,
        current_stage=stage,
    )
    context.logger.info("%s started.", stage.value)
    result = runner(context)
    context.logger.info("%s completed.", stage.value)
    return result
