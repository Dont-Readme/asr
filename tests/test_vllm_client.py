from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import unittest

from src.config import AppConfig
from src.clients.vllm_client import VLLMGenerateClient, VLLMOpenAIChatClient, extract_json_object


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        content_length = int(self.headers["Content-Length"])
        body = self.rfile.read(content_length)
        request_payload = json.loads(body.decode("utf-8"))
        if "messages" in request_payload:
            payload = {
                "choices": [
                    {
                        "message": {
                            "content": '{"meeting_title":"테스트","summary":["요약"],"decisions":[],"action_items":[]}'
                        }
                    }
                ]
            }
        else:
            payload = {"generated_text": '{"meeting_title":"테스트","summary":["요약"],"decisions":[],"action_items":[]}'}
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


class VllmClientTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()

    def test_generate_reads_generated_text(self) -> None:
        host, port = self.server.server_address
        config = AppConfig(
            project_root=__import__("pathlib").Path(".").resolve(),
            pipeline_mode="production",
            work_root=__import__("pathlib").Path("./work").resolve(),
            output_root=__import__("pathlib").Path("./output").resolve(),
            log_root=__import__("pathlib").Path("./logs").resolve(),
            input_root=__import__("pathlib").Path("./input").resolve(),
            device="cpu",
            asr_model="asr",
            align_model="align",
            diarization_model="diarize",
            asr_command="",
            align_command="",
            diarization_command="",
            hf_home=__import__("pathlib").Path("./.hf_cache").resolve(),
            huggingface_hub_token="",
            db_url="sqlite:///./work/app.sqlite3",
            summary_provider="vllm_generate",
            summary_base_url=f"http://{host}:{port}",
            summary_endpoint_path="/generate",
            summary_api_key="",
            summary_model="",
            summary_temperature=0.3,
            summary_top_p=0.9,
            summary_max_tokens=1000,
            summary_response_key="generated_text",
            audio_target_sr=16000,
            audio_target_channels=1,
            merge_ambiguous_sec=0.08,
            merge_ambiguous_ratio=0.2,
            backchannel_mode="keep",
        )
        client = VLLMGenerateClient(config)

        raw_text = client.generate("prompt")
        payload = extract_json_object(raw_text)

        self.assertEqual(payload["meeting_title"], "테스트")
        self.assertEqual(payload["summary"], ["요약"])

    def test_openai_chat_generate_reads_choices_message(self) -> None:
        host, port = self.server.server_address
        config = AppConfig(
            project_root=__import__("pathlib").Path(".").resolve(),
            pipeline_mode="production",
            work_root=__import__("pathlib").Path("./work").resolve(),
            output_root=__import__("pathlib").Path("./output").resolve(),
            log_root=__import__("pathlib").Path("./logs").resolve(),
            input_root=__import__("pathlib").Path("./input").resolve(),
            device="cpu",
            asr_model="asr",
            align_model="align",
            diarization_model="diarize",
            asr_command="",
            align_command="",
            diarization_command="",
            hf_home=__import__("pathlib").Path("./.hf_cache").resolve(),
            huggingface_hub_token="",
            db_url="sqlite:///./work/app.sqlite3",
            summary_provider="vllm_openai_chat",
            summary_base_url=f"http://{host}:{port}",
            summary_endpoint_path="/v1/chat/completions",
            summary_api_key="token-abc123",
            summary_model="gpt-oss-20b",
            summary_temperature=0.3,
            summary_top_p=0.9,
            summary_max_tokens=1000,
            summary_response_key="generated_text",
            audio_target_sr=16000,
            audio_target_channels=1,
            merge_ambiguous_sec=0.08,
            merge_ambiguous_ratio=0.2,
            backchannel_mode="keep",
        )
        client = VLLMOpenAIChatClient(config)

        raw_text = client.generate("prompt")
        payload = extract_json_object(raw_text)

        self.assertEqual(payload["meeting_title"], "테스트")
        self.assertEqual(payload["summary"], ["요약"])

    def test_generate_client_auto_switches_to_openai_chat_endpoint(self) -> None:
        host, port = self.server.server_address
        config = AppConfig(
            project_root=__import__("pathlib").Path(".").resolve(),
            pipeline_mode="production",
            work_root=__import__("pathlib").Path("./work").resolve(),
            output_root=__import__("pathlib").Path("./output").resolve(),
            log_root=__import__("pathlib").Path("./logs").resolve(),
            input_root=__import__("pathlib").Path("./input").resolve(),
            device="cpu",
            asr_model="asr",
            align_model="align",
            diarization_model="diarize",
            asr_command="",
            align_command="",
            diarization_command="",
            hf_home=__import__("pathlib").Path("./.hf_cache").resolve(),
            huggingface_hub_token="",
            db_url="sqlite:///./work/app.sqlite3",
            summary_provider="vllm_generate",
            summary_base_url=f"http://{host}:{port}",
            summary_endpoint_path="/v1/chat/completions",
            summary_api_key="token-abc123",
            summary_model="gpt-oss-120b",
            summary_temperature=0.3,
            summary_top_p=0.9,
            summary_max_tokens=1000,
            summary_response_key="generated_text",
            audio_target_sr=16000,
            audio_target_channels=1,
            merge_ambiguous_sec=0.08,
            merge_ambiguous_ratio=0.2,
            backchannel_mode="keep",
        )
        client = VLLMGenerateClient(config)

        raw_text = client.generate("prompt")
        payload = extract_json_object(raw_text)

        self.assertEqual(payload["meeting_title"], "테스트")
        self.assertEqual(payload["summary"], ["요약"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
