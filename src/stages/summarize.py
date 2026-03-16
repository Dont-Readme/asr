from __future__ import annotations

import json

from src.clients.vllm_client import VLLMGenerateClient, extract_json_object
from src.pipeline.job_context import JobContext
from src.schemas.summary import ActionItem, MeetingSummary
from src.schemas.transcript import TranscriptResult
from src.utils.errors import StageError
from src.utils.paths import compute_sha256


def run(context: JobContext) -> MeetingSummary:
    transcript = TranscriptResult.from_dict(json.loads(context.transcript_json_path.read_text(encoding="utf-8")))

    if context.config.summary_provider == "mock":
        summary = _build_mock_summary(context, transcript)
    elif context.config.summary_provider == "vllm_generate":
        prompt = _render_prompt(context, transcript)
        client = VLLMGenerateClient(context.config)
        raw_text = client.generate(prompt)
        payload = extract_json_object(raw_text)
        payload["provider"] = "vllm_generate"
        summary = MeetingSummary.from_dict(payload)
    else:
        raise StageError("SUMMARIZE", f"지원하지 않는 SUMMARY_PROVIDER: {context.config.summary_provider}")

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
    prompt_template = (context.config.project_root / "src" / "prompts" / "summary_ko.txt").read_text(
        encoding="utf-8"
    )
    transcript_text = "\n".join(segment.line for segment in transcript.segments)
    return prompt_template.format(
        meeting_title=context.meeting_title,
        transcript=transcript_text,
    )


def _build_mock_summary(context: JobContext, transcript: TranscriptResult) -> MeetingSummary:
    lines = [segment.text for segment in transcript.segments[:3]]
    summary = lines[:2] or [f"{context.meeting_title} 회의가 진행되었다."]
    decisions = [lines[2]] if len(lines) >= 3 else ["결정사항은 후속 검토가 필요하다."]
    action_items = [
        ActionItem(
            owner="미정",
            deadline="미정",
            task="회의에서 언급된 후속 작업을 검토하고 담당자를 지정한다.",
        )
    ]
    return MeetingSummary(
        meeting_title=context.meeting_title,
        provider="mock",
        summary=summary,
        decisions=decisions,
        action_items=action_items,
    )
