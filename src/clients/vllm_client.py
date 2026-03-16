from __future__ import annotations

import json
from urllib import error, request

from src.config import AppConfig
from src.utils.errors import StageError


class VLLMGenerateClient:
    def __init__(self, config: AppConfig):
        self.config = config

    def generate(self, prompt: str) -> str:
        if _looks_like_openai_chat_endpoint(self.config.summary_endpoint_path):
            return VLLMOpenAIChatClient(self.config).generate(prompt)

        payload = {
            "prompt": prompt,
            "temperature": self.config.summary_temperature,
            "top_p": self.config.summary_top_p,
            "max_tokens": self.config.summary_max_tokens,
        }
        try:
            parsed = _post_json(self.config, payload)
        except StageError as exc:
            if _should_retry_as_openai_chat(self.config, str(exc)):
                return VLLMOpenAIChatClient(self.config).generate(prompt)
            raise
        value = parsed.get(self.config.summary_response_key)
        if not isinstance(value, str):
            raise StageError(
                "SUMMARIZE",
                f"vLLM 응답에 {self.config.summary_response_key} 문자열 필드가 없습니다.",
            )
        return value


class VLLMOpenAIChatClient:
    def __init__(self, config: AppConfig):
        self.config = config

    def generate(self, prompt: str) -> str:
        if not self.config.summary_model.strip():
            raise StageError("SUMMARIZE", "SUMMARY_MODEL is required for vllm_openai_chat.")

        payload = {
            "model": self.config.summary_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": self.config.summary_temperature,
            "top_p": self.config.summary_top_p,
            "max_tokens": self.config.summary_max_tokens,
        }
        parsed = _post_json(self.config, payload)
        return extract_openai_chat_content(parsed)


def _looks_like_openai_chat_endpoint(endpoint_path: str) -> bool:
    normalized = endpoint_path.rstrip("/").lower()
    return normalized.endswith("/chat/completions")


def _should_retry_as_openai_chat(config: AppConfig, error_text: str) -> bool:
    if not config.summary_model.strip():
        return False
    normalized = error_text.lower()
    return "messages" in normalized and "field required" in normalized


def _post_json(config: AppConfig, payload: dict) -> dict:
    url = f"{config.summary_base_url.rstrip('/')}{config.summary_endpoint_path}"
    headers = {
        "Content-Type": "application/json",
    }
    if config.summary_api_key:
        headers["Authorization"] = f"Bearer {config.summary_api_key}"

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
    return json.loads(raw_response)


def extract_openai_chat_content(payload: dict) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise StageError("SUMMARIZE", "OpenAI 호환 응답에 choices가 없습니다.")

    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise StageError("SUMMARIZE", "OpenAI 호환 응답에 message가 없습니다.")

    content = message.get("content")
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_value = item.get("text")
                if isinstance(text_value, str):
                    text_parts.append(text_value)
        if text_parts:
            return "\n".join(text_parts)

    raise StageError("SUMMARIZE", "OpenAI 호환 응답에서 텍스트 content를 찾지 못했습니다.")


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
