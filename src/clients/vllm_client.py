from __future__ import annotations

import json
from urllib import error, request

from src.config import AppConfig
from src.utils.errors import StageError


class VLLMGenerateClient:
    def __init__(self, config: AppConfig):
        self.config = config

    def generate(self, prompt: str) -> str:
        url = f"{self.config.summary_base_url.rstrip('/')}{self.config.summary_endpoint_path}"
        payload = {
            "prompt": prompt,
            "temperature": self.config.summary_temperature,
            "top_p": self.config.summary_top_p,
            "max_tokens": self.config.summary_max_tokens,
        }
        headers = {
            "Content-Type": "application/json",
        }
        if self.config.summary_api_key:
            headers["Authorization"] = f"Bearer {self.config.summary_api_key}"

        req = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=60) as response:
                raw_response = response.read().decode("utf-8")
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise StageError("SUMMARIZE", f"vLLM HTTP {exc.code}: {body}") from exc
        except error.URLError as exc:
            raise StageError("SUMMARIZE", f"vLLM 연결 실패: {exc.reason}") from exc

        parsed = json.loads(raw_response)
        value = parsed.get(self.config.summary_response_key)
        if not isinstance(value, str):
            raise StageError(
                "SUMMARIZE",
                f"vLLM 응답에 {self.config.summary_response_key} 문자열 필드가 없습니다.",
            )
        return value


def extract_json_object(raw_text: str) -> dict:
    stripped = raw_text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            stripped = "\n".join(lines[1:-1]).strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise StageError("SUMMARIZE", "요약 응답에서 JSON 객체를 찾지 못했습니다.")
        try:
            return json.loads(stripped[start : end + 1])
        except json.JSONDecodeError as exc:
            raise StageError("SUMMARIZE", "요약 응답 JSON 파싱 실패") from exc
