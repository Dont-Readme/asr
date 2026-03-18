from __future__ import annotations

import json

from src.pipeline.job_context import JobContext
from src.schemas.summary import MeetingSummary
from src.schemas.transcript import TranscriptResult
from src.services.summary_generation import render_summary_prompt, summarize_transcript
from src.utils.paths import compute_sha256


def run(context: JobContext) -> MeetingSummary:
    transcript = TranscriptResult.from_dict(json.loads(context.transcript_json_path.read_text(encoding="utf-8")))
    summary = summarize_transcript(
        context.config,
        meeting_title=context.meeting_title,
        transcript=transcript,
    )

    context.summary_json_path.write_text(
        json.dumps(summary.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    context.repo.register_artifact(
        context.job_id,
        "summary_json",
        context.summary_json_path,
        compute_sha256(context.summary_json_path),
    )
    return summary


def _render_prompt(context: JobContext, transcript: TranscriptResult) -> str:
    return render_summary_prompt(
        context.config,
        meeting_title=context.meeting_title,
        transcript=transcript,
    )
