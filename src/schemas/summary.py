from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ActionItem:
    owner: str
    deadline: str
    task: str

    @classmethod
    def from_dict(cls, payload: dict) -> "ActionItem":
        return cls(
            owner=payload.get("owner", "미정"),
            deadline=payload.get("deadline", "미정"),
            task=payload.get("task", ""),
        )

    def to_dict(self) -> dict:
        return {
            "owner": self.owner,
            "deadline": self.deadline,
            "task": self.task,
        }


@dataclass(slots=True)
class MeetingSummary:
    meeting_title: str
    provider: str
    summary: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    action_items: list[ActionItem] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict) -> "MeetingSummary":
        return cls(
            meeting_title=payload.get("meeting_title", "회의"),
            provider=payload.get("provider", "unknown"),
            summary=list(payload.get("summary", [])),
            decisions=list(payload.get("decisions", [])),
            action_items=[ActionItem.from_dict(item) for item in payload.get("action_items", [])],
        )

    def to_dict(self) -> dict:
        return {
            "meeting_title": self.meeting_title,
            "provider": self.provider,
            "summary": self.summary,
            "decisions": self.decisions,
            "action_items": [item.to_dict() for item in self.action_items],
        }
