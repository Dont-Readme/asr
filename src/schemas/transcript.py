from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class TranscriptWord:
    text: str
    start_sec: float
    end_sec: float
    speaker_label: str

    @classmethod
    def from_dict(cls, payload: dict) -> "TranscriptWord":
        return cls(
            text=payload["text"],
            start_sec=payload["start_sec"],
            end_sec=payload["end_sec"],
            speaker_label=payload["speaker_label"],
        )

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "start_sec": self.start_sec,
            "end_sec": self.end_sec,
            "speaker_label": self.speaker_label,
        }


@dataclass(slots=True)
class TranscriptSegment:
    speaker_label: str
    start_sec: float
    end_sec: float
    text: str
    line: str
    words: list[TranscriptWord] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict) -> "TranscriptSegment":
        return cls(
            speaker_label=payload["speaker_label"],
            start_sec=payload["start_sec"],
            end_sec=payload["end_sec"],
            text=payload["text"],
            line=payload["line"],
            words=[TranscriptWord.from_dict(word) for word in payload.get("words", [])],
        )

    def to_dict(self) -> dict:
        return {
            "speaker_label": self.speaker_label,
            "start_sec": self.start_sec,
            "end_sec": self.end_sec,
            "text": self.text,
            "line": self.line,
            "words": [word.to_dict() for word in self.words],
        }


@dataclass(slots=True)
class TranscriptResult:
    meeting_title: str
    provider: str
    segments: list[TranscriptSegment]

    @classmethod
    def from_dict(cls, payload: dict) -> "TranscriptResult":
        return cls(
            meeting_title=payload["meeting_title"],
            provider=payload["provider"],
            segments=[TranscriptSegment.from_dict(segment) for segment in payload.get("segments", [])],
        )

    def to_dict(self) -> dict:
        return {
            "meeting_title": self.meeting_title,
            "provider": self.provider,
            "segments": [segment.to_dict() for segment in self.segments],
            "lines": [segment.line for segment in self.segments],
        }
