from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SpeakerTurn:
    speaker_label: str
    start_sec: float
    end_sec: float

    @classmethod
    def from_dict(cls, payload: dict) -> "SpeakerTurn":
        return cls(
            speaker_label=payload["speaker_label"],
            start_sec=payload["start_sec"],
            end_sec=payload["end_sec"],
        )

    def to_dict(self) -> dict:
        return {
            "speaker_label": self.speaker_label,
            "start_sec": self.start_sec,
            "end_sec": self.end_sec,
        }


@dataclass(slots=True)
class DiarizationResult:
    provider: str
    model: str
    speakers: list[SpeakerTurn]

    @classmethod
    def from_dict(cls, payload: dict) -> "DiarizationResult":
        return cls(
            provider=payload["provider"],
            model=payload["model"],
            speakers=[SpeakerTurn.from_dict(item) for item in payload.get("speakers", [])],
        )

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "speakers": [speaker.to_dict() for speaker in self.speakers],
        }
