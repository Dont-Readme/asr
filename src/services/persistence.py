from __future__ import annotations

import json

from src.db.models import TranscriptSegmentRecord
from src.pipeline.job_context import JobContext
from src.schemas.summary import MeetingSummary
from src.schemas.transcript import TranscriptResult


def persist_transcript_records(context: JobContext, transcript: TranscriptResult) -> None:
    records = [
        TranscriptSegmentRecord(
            speaker_label=segment.speaker_label,
            start_ms=int(segment.start_sec * 1000),
            end_ms=int(segment.end_sec * 1000),
            text=segment.text,
            words_json=json.dumps(
                [word.to_dict() for word in segment.words],
                ensure_ascii=False,
            ),
        )
        for segment in transcript.segments
    ]
    context.repo.replace_transcript_segments(context.job_id, records)


def persist_summary_result(context: JobContext, summary: MeetingSummary) -> None:
    context.repo.upsert_summary(context.job_id, summary.to_dict())
