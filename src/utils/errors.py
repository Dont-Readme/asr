from __future__ import annotations


class PipelineError(Exception):
    """Base pipeline exception."""


class ConfigurationError(PipelineError):
    """Raised when required settings are missing."""


class StageError(PipelineError):
    """Raised when a stage cannot complete."""

    def __init__(self, stage: str, message: str):
        super().__init__(message)
        self.stage = stage
        self.message = message

    def __str__(self) -> str:
        return f"[{self.stage}] {self.message}"
