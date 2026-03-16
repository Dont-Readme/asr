from __future__ import annotations

import json

from src.pipeline.job_context import JobContext
from src.schemas.summary import MeetingSummary
from src.schemas.transcript import TranscriptResult
from src.utils.paths import compute_sha256
from src.utils.time import utcnow_iso


def run(context: JobContext):
    transcript = TranscriptResult.from_dict(json.loads(context.transcript_json_path.read_text(encoding="utf-8")))
    summary = MeetingSummary.from_dict(json.loads(context.summary_json_path.read_text(encoding="utf-8")))

    lines: list[str] = [
        f"회의명: {context.meeting_title}",
        f"생성시각(UTC): {utcnow_iso()}",
        "",
        "[핵심 요약]",
    ]
    lines.extend(_render_bullets(summary.summary, fallback="요약이 없습니다."))
    lines.extend(["", "[결정사항]"])
    lines.extend(_render_numbered(summary.decisions, fallback="결정사항이 없습니다."))
    lines.extend(["", "[액션 아이템]"])
    if summary.action_items:
        for index, item in enumerate(summary.action_items, start=1):
            lines.append(f"{index}. 담당자: {item.owner} | 기한: {item.deadline} | 내용: {item.task}")
    else:
        lines.append("1. 담당자: 미정 | 기한: 미정 | 내용: 액션 아이템이 없습니다.")

    lines.extend(["", "[화자 포함 전사]"])
    lines.extend(segment.line for segment in transcript.segments)
    lines.append("")

    context.meeting_notes_path.write_text("\n".join(lines), encoding="utf-8")
    context.repo.register_artifact(
        context.job_id,
        "meeting_notes_txt",
        context.meeting_notes_path,
        compute_sha256(context.meeting_notes_path),
    )
    return context.meeting_notes_path


def _render_bullets(items: list[str], *, fallback: str) -> list[str]:
    if not items:
        return [f"- {fallback}"]
    return [f"- {item}" for item in items]


def _render_numbered(items: list[str], *, fallback: str) -> list[str]:
    if not items:
        return [f"1. {fallback}"]
    return [f"{index}. {item}" for index, item in enumerate(items, start=1)]
