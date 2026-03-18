from __future__ import annotations

import json
from urllib import error, request

from src.config import AppConfig
from src.utils.errors import StageError


class FeatureApiClient:
    def __init__(self, config: AppConfig):
        self.config = config

    def transcribe_meeting_by_path(
        self,
        *,
        audio_path: str,
        language: str = "ko",
        context: str | None = None,
    ) -> dict:
        payload = {
            "audio_path": audio_path,
            "language": language,
            "context": context,
        }
        return self._post_json(
            stage="ASR",
            url=f"{self.config.transcribe_api_base_url.rstrip('/')}/meeting-transcriptions/by-path",
            payload=payload,
        )

    def diarize_by_path(
        self,
        *,
        audio_path: str,
        num_speakers: int | None = None,
        min_speakers: int | None = None,
        max_speakers: int | None = None,
    ) -> dict:
        payload = {
            "audio_path": audio_path,
            "num_speakers": num_speakers,
            "min_speakers": min_speakers,
            "max_speakers": max_speakers,
        }
        return self._post_json(
            stage="DIARIZE",
            url=f"{self.config.diarize_api_base_url.rstrip('/')}/diarizations/by-path",
            payload=payload,
        )

    def summarize_transcript(
        self,
        *,
        meeting_title: str,
        transcript: dict,
    ) -> dict:
        payload = {
            "meeting_title": meeting_title,
            "transcript": transcript,
        }
        return self._post_json(
            stage="SUMMARIZE",
            url=f"{self.config.summarize_api_base_url.rstrip('/')}/summaries",
            payload=payload,
        )

    def _post_json(self, *, stage: str, url: str, payload: dict) -> dict:
        req = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=300) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise StageError(stage, f"feature API HTTP {exc.code}: {body}") from exc
        except error.URLError as exc:
            raise StageError(stage, f"feature API 연결 실패: {exc.reason}") from exc
