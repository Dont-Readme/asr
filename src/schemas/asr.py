from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class AsrWord:
    text: str
    start_sec: float | None = None
    end_sec: float | None = None

    @classmethod
    def from_dict(cls, payload: dict) -> "AsrWord":
        return cls(
            text=payload["text"],
            start_sec=payload.get("start_sec"),
            end_sec=payload.get("end_sec"),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class AsrSegment:
    text: str
    start_sec: float
    end_sec: float
    words: list[AsrWord] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict) -> "AsrSegment":
        return cls(
            text=payload["text"],
            start_sec=payload["start_sec"],
            end_sec=payload["end_sec"],
            words=[AsrWord.from_dict(word) for word in payload.get("words", [])],
        )

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "start_sec": self.start_sec,
            "end_sec": self.end_sec,
            "words": [word.to_dict() for word in self.words],
        }


@dataclass(slots=True)
class AsrResult:
    provider: str
    model: str
    language: str
    segments: list[AsrSegment]

    @classmethod
    def from_dict(cls, payload: dict) -> "AsrResult":
        return cls(
            provider=payload["provider"],
            model=payload["model"],
            language=payload.get("language", "ko"),
            segments=[AsrSegment.from_dict(segment) for segment in payload.get("segments", [])],
        )

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "language": self.language,
            "segments": [segment.to_dict() for segment in self.segments],
        }
