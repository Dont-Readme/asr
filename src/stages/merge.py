from __future__ import annotations

import json

from src.pipeline.job_context import JobContext
from src.schemas.align import AlignResult
from src.schemas.diarization import DiarizationResult, SpeakerTurn
from src.schemas.transcript import TranscriptResult, TranscriptSegment, TranscriptWord
from src.utils.paths import compute_sha256
from src.utils.time import format_seconds_hhmmss

BACKCHANNEL_TOKENS = {
    "네",
    "예",
    "응",
    "음",
    "아",
    "그래요",
    "맞아요",
    "좋습니다",
}


def run(context: JobContext) -> TranscriptResult:
    align_result = AlignResult.from_dict(json.loads(context.align_json_path.read_text(encoding="utf-8")))
    diarization_result = DiarizationResult.from_dict(
        json.loads(context.diarization_json_path.read_text(encoding="utf-8"))
    )

    raw_segments = _merge_words_with_speakers(context, align_result, diarization_result)
    transcript = TranscriptResult(
        meeting_title=context.meeting_title,
        provider="overlap_policy_v1",
        segments=raw_segments,
    )
    context.transcript_json_path.write_text(
        json.dumps(transcript.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    context.repo.register_artifact(
        context.job_id,
        "transcript_diarized_json",
        context.transcript_json_path,
        compute_sha256(context.transcript_json_path),
    )
    return transcript


def _merge_words_with_speakers(
    context: JobContext,
    align_result: AlignResult,
    diarization_result: DiarizationResult,
) -> list[TranscriptSegment]:
    word_buffer: list[TranscriptWord] = []
    previous_speaker: str | None = None

    for segment in align_result.segments:
        words = segment.words or [
            type("TmpWord", (), {"text": segment.text, "start_sec": segment.start_sec, "end_sec": segment.end_sec})
        ]
        for word in words:
            speaker = _choose_speaker(
                start_sec=word.start_sec,
                end_sec=word.end_sec,
                turns=diarization_result.speakers,
                previous_speaker=previous_speaker,
                ambiguous_sec=context.config.merge_ambiguous_sec,
                ambiguous_ratio=context.config.merge_ambiguous_ratio,
            )
            word_buffer.append(
                TranscriptWord(
                    text=word.text,
                    start_sec=word.start_sec,
                    end_sec=word.end_sec,
                    speaker_label=speaker,
                )
            )
            previous_speaker = speaker

    grouped = _group_words(word_buffer)
    filtered = _apply_backchannel_policy(grouped, context.backchannel_mode)
    return _normalize_speaker_labels(filtered)


def _group_words(words: list[TranscriptWord]) -> list[TranscriptSegment]:
    if not words:
        return []

    grouped: list[TranscriptSegment] = []
    current_words: list[TranscriptWord] = [words[0]]

    for word in words[1:]:
        previous_word = current_words[-1]
        if (
            word.speaker_label == previous_word.speaker_label
            and word.start_sec - previous_word.end_sec <= 1.0
        ):
            current_words.append(word)
            continue

        grouped.append(_build_segment(current_words))
        current_words = [word]

    grouped.append(_build_segment(current_words))
    return grouped


def _build_segment(words: list[TranscriptWord]) -> TranscriptSegment:
    text = _join_tokens([word.text for word in words])
    start_sec = words[0].start_sec
    end_sec = words[-1].end_sec
    line = f"[{format_seconds_hhmmss(start_sec)}] {words[0].speaker_label}: {text}"
    return TranscriptSegment(
        speaker_label=words[0].speaker_label,
        start_sec=start_sec,
        end_sec=end_sec,
        text=text,
        line=line,
        words=words,
    )


def _apply_backchannel_policy(
    segments: list[TranscriptSegment],
    backchannel_mode: str,
) -> list[TranscriptSegment]:
    if backchannel_mode == "keep":
        return segments

    updated: list[TranscriptSegment] = []
    for segment in segments:
        is_backchannel = _is_backchannel(segment.text)
        if backchannel_mode == "drop" and is_backchannel:
            continue
        if backchannel_mode == "tag" and is_backchannel:
            segment = TranscriptSegment(
                speaker_label=segment.speaker_label,
                start_sec=segment.start_sec,
                end_sec=segment.end_sec,
                text=f"(추임새) {segment.text}",
                line=segment.line,
                words=segment.words,
            )
        updated.append(segment)
    return updated


def _normalize_speaker_labels(segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
    label_map: dict[str, str] = {}
    next_index = 0
    normalized: list[TranscriptSegment] = []

    for segment in segments:
        raw_label = segment.speaker_label
        if raw_label not in label_map:
            suffix = chr(ord("A") + next_index) if next_index < 26 else str(next_index + 1)
            label_map[raw_label] = f"화자 {suffix}"
            next_index += 1
        display_label = label_map[raw_label]
        line = f"[{format_seconds_hhmmss(segment.start_sec)}] {display_label}: {segment.text}"
        normalized.append(
            TranscriptSegment(
                speaker_label=display_label,
                start_sec=segment.start_sec,
                end_sec=segment.end_sec,
                text=segment.text,
                line=line,
                words=[
                    TranscriptWord(
                        text=word.text,
                        start_sec=word.start_sec,
                        end_sec=word.end_sec,
                        speaker_label=display_label,
                    )
                    for word in segment.words
                ],
            )
        )
    return normalized


def _choose_speaker(
    *,
    start_sec: float,
    end_sec: float,
    turns: list[SpeakerTurn],
    previous_speaker: str | None,
    ambiguous_sec: float,
    ambiguous_ratio: float,
) -> str:
    scores: dict[str, float] = {}
    for turn in turns:
        overlap = _overlap(start_sec, end_sec, turn.start_sec, turn.end_sec)
        if overlap > 0:
            scores[turn.speaker_label] = scores.get(turn.speaker_label, 0.0) + overlap

    if scores:
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        top_label, top_score = ranked[0]
        if len(ranked) > 1:
            second_score = ranked[1][1]
            duration = max(end_sec - start_sec, 1e-6)
            score_gap = top_score - second_score
            is_ambiguous = score_gap < ambiguous_sec or (score_gap / duration) < ambiguous_ratio
            if is_ambiguous and previous_speaker in scores:
                return previous_speaker
        return top_label

    if not turns:
        return "speaker_unknown"

    nearest = min(turns, key=lambda turn: _distance_to_range(start_sec, end_sec, turn.start_sec, turn.end_sec))
    return nearest.speaker_label


def _overlap(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def _distance_to_range(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    if _overlap(start_a, end_a, start_b, end_b) > 0:
        return 0.0
    if end_a <= start_b:
        return start_b - end_a
    return start_a - end_b


def _join_tokens(tokens: list[str]) -> str:
    text = " ".join(token.strip() for token in tokens if token.strip())
    for punctuation in [".", ",", "!", "?", ":", ";"]:
        text = text.replace(f" {punctuation}", punctuation)
    return text


def _is_backchannel(text: str) -> bool:
    normalized = text.strip().rstrip(".,!?").replace("(추임새) ", "")
    token_count = len(normalized.split())
    return token_count <= 3 and normalized in BACKCHANNEL_TOKENS
