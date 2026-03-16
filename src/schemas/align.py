from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AlignedWord:
    text: str
    start_sec: float
    end_sec: float

    @classmethod
    def from_dict(cls, payload: dict) -> "AlignedWord":
        return cls(
            text=payload["text"],
            start_sec=payload["start_sec"],
            end_sec=payload["end_sec"],
        )

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "start_sec": self.start_sec,
            "end_sec": self.end_sec,
        }


@dataclass(slots=True)
class AlignedSegment:
    text: str
    start_sec: float
    end_sec: float
    words: list[AlignedWord] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict) -> "AlignedSegment":
        return cls(
            text=payload["text"],
            start_sec=payload["start_sec"],
            end_sec=payload["end_sec"],
            words=[AlignedWord.from_dict(word) for word in payload.get("words", [])],
        )

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "start_sec": self.start_sec,
            "end_sec": self.end_sec,
            "words": [word.to_dict() for word in self.words],
        }


@dataclass(slots=True)
class AlignResult:
    provider: str
    model: str
    segments: list[AlignedSegment]

    @classmethod
    def from_dict(cls, payload: dict) -> "AlignResult":
        return cls(
            provider=payload["provider"],
            model=payload["model"],
            segments=[AlignedSegment.from_dict(segment) for segment in payload.get("segments", [])],
        )

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "segments": [segment.to_dict() for segment in self.segments],
        }
