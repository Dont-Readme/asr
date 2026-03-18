from __future__ import annotations

from src.clients.vllm_client import VLLMGenerateClient, VLLMOpenAIChatClient, extract_json_object
from src.config import AppConfig
from src.schemas.summary import ActionItem, MeetingSummary
from src.schemas.transcript import TranscriptResult
from src.utils.errors import StageError


def summarize_transcript(
    config: AppConfig,
    *,
    meeting_title: str,
    transcript: TranscriptResult,
) -> MeetingSummary:
    if config.summary_provider == "mock":
        return build_mock_summary(meeting_title, transcript)

    prompt = render_summary_prompt(config, meeting_title=meeting_title, transcript=transcript)
    if config.summary_provider == "vllm_generate":
        client = VLLMGenerateClient(config)
        raw_text = client.generate(prompt)
        payload = extract_json_object(raw_text)
        payload["provider"] = "vllm_generate"
        return MeetingSummary.from_dict(payload)

    if config.summary_provider == "vllm_openai_chat":
        client = VLLMOpenAIChatClient(config)
        raw_text = client.generate(prompt)
        payload = extract_json_object(raw_text)
        payload["provider"] = "vllm_openai_chat"
        return MeetingSummary.from_dict(payload)

    raise StageError("SUMMARIZE", f"지원하지 않는 SUMMARY_PROVIDER: {config.summary_provider}")


def render_summary_prompt(
    config: AppConfig,
    *,
    meeting_title: str,
    transcript: TranscriptResult,
) -> str:
    prompt_template = (config.project_root / "src" / "prompts" / "summary_ko.txt").read_text(
        encoding="utf-8"
    )
    transcript_text = "\n".join(segment.line for segment in transcript.segments)
    return (
        prompt_template
        .replace("{meeting_title}", meeting_title)
        .replace("{transcript}", transcript_text)
    )


def build_mock_summary(meeting_title: str, transcript: TranscriptResult) -> MeetingSummary:
    lines = [segment.text for segment in transcript.segments[:3]]
    summary = lines[:2] or [f"{meeting_title} 회의가 진행되었다."]
    decisions = [lines[2]] if len(lines) >= 3 else ["결정사항은 후속 검토가 필요하다."]
    action_items = [
        ActionItem(
            owner="미정",
            deadline="미정",
            task="회의에서 언급된 후속 작업을 검토하고 담당자를 지정한다.",
        )
    ]
    return MeetingSummary(
        meeting_title=meeting_title,
        provider="mock",
        summary=summary,
        decisions=decisions,
        action_items=action_items,
    )
