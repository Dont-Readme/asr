from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil

from src.db.models import JobStage
from src.pipeline.job_context import JobContext
from src.schemas.summary import MeetingSummary
from src.services.common import mark_feature_done, mark_feature_failed, run_feature_stage
from src.stages import summarize


@dataclass(slots=True)
class SummaryArtifacts:
    transcript_json_path: Path
    summary_json_path: Path
    result: MeetingSummary


def run_summary(context: JobContext, *, transcript_path: Path | None = None) -> SummaryArtifacts:
    try:
        if transcript_path:
            _prime_transcript_json(context, transcript_path)
        result = run_feature_stage(context, JobStage.SUMMARIZE, summarize.run)
        mark_feature_done(context, JobStage.SUMMARIZE)
        return SummaryArtifacts(
            transcript_json_path=context.transcript_json_path,
            summary_json_path=context.summary_json_path,
            result=result,
        )
    except Exception as error:
        mark_feature_failed(context, "SUMMARIZE", error)
        raise


def _prime_transcript_json(context: JobContext, transcript_path: Path) -> None:
    resolved_source = transcript_path.expanduser().resolve()
    context.output_dir.mkdir(parents=True, exist_ok=True)
    if resolved_source != context.transcript_json_path:
        shutil.copyfile(resolved_source, context.transcript_json_path)
