from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from src.runtime.diarization_runtime import ResidentDiarizationResult
from src.runtime.transcription_runtime import ResidentTranscriptionResult
from src.schemas.summary import MeetingSummary
from src.services.meeting_note_jobs import MeetingNoteJobService, SubmittedMeetingNoteJob

try:
    from fastapi.testclient import TestClient
    from src.api.app import create_app as create_orchestration_app
    from src.api.diarize_app import create_app as create_diarize_app
    from src.api.summarize_app import create_app as create_summarize_app
    from src.api.transcribe_app import create_app as create_transcribe_app
except ImportError:  # pragma: no cover - api group missing
    TestClient = None
    create_orchestration_app = None
    create_diarize_app = None
    create_summarize_app = None
    create_transcribe_app = None


@unittest.skipIf(TestClient is None, "fastapi test dependencies are not installed")
class ApiStructureTest(unittest.TestCase):
    def test_transcribe_app_splits_voice_and_meeting_routes(self) -> None:
        class FakeRuntime:
            def __init__(self) -> None:
                self.project_root = Path(tempfile.mkdtemp(prefix="transcribe-api-"))

            def metadata(self) -> dict[str, object]:
                return {
                    "status": "ready",
                    "loaded_at": "2026-03-18T00:00:00Z",
                    "process_id": 123,
                    "device": "cuda",
                    "models": {"asr": "fake-asr", "align": "fake-align"},
                }

            def voice_transcribe(self, **kwargs) -> ResidentTranscriptionResult:
                if not kwargs["audio_path"].exists():  # pragma: no cover
                    raise AssertionError("audio path was not materialized")
                return ResidentTranscriptionResult(
                    asr={"segments": [{"text": "음성 입력"}]},
                    align=None,
                    elapsed_sec=0.12,
                )

            def meeting_transcribe(self, **kwargs) -> ResidentTranscriptionResult:
                if not kwargs["audio_path"].exists():  # pragma: no cover
                    raise AssertionError("audio path was not materialized")
                return ResidentTranscriptionResult(
                    asr={"segments": [{"text": "회의 시작"}]},
                    align={"segments": [{"text": "회의 시작"}]},
                    elapsed_sec=0.34,
                )

        client = TestClient(create_transcribe_app(runtime=FakeRuntime()))

        with tempfile.NamedTemporaryFile(suffix=".wav") as audio_file:
            voice_response = client.post(
                "/voice-transcriptions/by-path",
                json={"audio_path": audio_file.name, "language": "ko"},
            )
            meeting_response = client.post(
                "/meeting-transcriptions/by-path",
                json={"audio_path": audio_file.name, "language": "ko"},
            )

        self.assertEqual(voice_response.status_code, 200)
        self.assertEqual(voice_response.json()["text"], "음성 입력")
        self.assertEqual(meeting_response.status_code, 200)
        self.assertEqual(meeting_response.json()["text"], "회의 시작")
        self.assertIn("align", meeting_response.json())

    def test_diarize_app_accepts_upload(self) -> None:
        class FakeRuntime:
            def __init__(self) -> None:
                self.project_root = Path(tempfile.mkdtemp(prefix="diarize-api-"))

            def metadata(self) -> dict[str, object]:
                return {
                    "status": "ready",
                    "loaded_at": "2026-03-18T00:00:00Z",
                    "process_id": 123,
                    "device": "cuda",
                    "models": {"diarization": "fake-diarize"},
                }

            def diarize(self, **kwargs) -> ResidentDiarizationResult:
                if not kwargs["audio_path"].exists():  # pragma: no cover
                    raise AssertionError("audio path was not materialized")
                return ResidentDiarizationResult(
                    diarization={"speakers": [{"speaker_label": "speaker_0", "start_sec": 0.0, "end_sec": 1.0}]},
                    rttm="SPEAKER meeting 1 0.000 1.000 <NA> <NA> speaker_0 <NA> <NA>",
                    elapsed_sec=0.45,
                )

        client = TestClient(create_diarize_app(runtime=FakeRuntime()))
        response = client.post(
            "/diarizations/upload",
            files={"file": ("sample.wav", b"fake-audio", "audio/wav")},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["diarization"]["speakers"][0]["speaker_label"], "speaker_0")

    def test_summarize_app_accepts_transcript_payload(self) -> None:
        def fake_summary_fn(config, *, meeting_title: str, transcript):
            del config, transcript
            return MeetingSummary(
                meeting_title=meeting_title,
                provider="mock",
                summary=["핵심 요약"],
                decisions=["결정사항"],
                action_items=[],
            )

        client = TestClient(create_summarize_app(summary_fn=fake_summary_fn))
        response = client.post(
            "/summaries",
            json={
                "meeting_title": "주간 회의",
                "transcript": {
                    "provider": "overlap_policy_v1",
                    "segments": [
                        {
                            "speaker_label": "화자 A",
                            "start_sec": 0.0,
                            "end_sec": 1.0,
                            "text": "안녕하세요",
                            "line": "[00:00:00] 화자 A: 안녕하세요",
                            "words": [],
                        }
                    ],
                },
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["summary"]["meeting_title"], "주간 회의")

    def test_orchestration_app_returns_job_acceptance_response(self) -> None:
        class FakeJobService:
            def submit_path_job(self, **kwargs) -> SubmittedMeetingNoteJob:
                del kwargs
                return SubmittedMeetingNoteJob(job_id="job-123", meeting_title="회의")

        client = TestClient(create_orchestration_app(job_service=FakeJobService()))
        response = client.post(
            "/meeting-note-jobs/by-path",
            json={"audio_path": "/tmp/input.m4a", "meeting_title": "회의"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["job_id"], "job-123")
        self.assertEqual(response.json()["status"], "PENDING")


class MeetingNoteJobServiceTest(unittest.TestCase):
    def test_meeting_note_job_service_builds_transcript_summary_and_notes(self) -> None:
        class FakeFeatureClient:
            def transcribe_meeting_by_path(self, **kwargs) -> dict:
                del kwargs
                return {
                    "asr": {
                        "provider": "qwen_asr",
                        "model": "fake-asr",
                        "language": "Korean",
                        "segments": [{"text": "안녕하세요", "start_sec": 0.0, "end_sec": 1.0, "words": []}],
                    },
                    "align": {
                        "provider": "qwen_forced_aligner",
                        "model": "fake-align",
                        "segments": [
                            {
                                "text": "안녕하세요",
                                "start_sec": 0.0,
                                "end_sec": 1.0,
                                "words": [{"text": "안녕하세요", "start_sec": 0.0, "end_sec": 1.0}],
                            }
                        ],
                    },
                    "elapsed_sec": 0.1,
                }

            def diarize_by_path(self, **kwargs) -> dict:
                del kwargs
                return {
                    "diarization": {
                        "provider": "pyannote.audio",
                        "model": "fake-diarize",
                        "speakers": [{"speaker_label": "speaker_0", "start_sec": 0.0, "end_sec": 1.0}],
                    },
                    "rttm": "SPEAKER meeting 1 0.000 1.000 <NA> <NA> speaker_0 <NA> <NA>",
                    "elapsed_sec": 0.2,
                }

            def summarize_transcript(self, **kwargs) -> dict:
                del kwargs
                return {
                    "summary": {
                        "meeting_title": "회의",
                        "provider": "mock",
                        "summary": ["핵심 요약"],
                        "decisions": ["결정사항"],
                        "action_items": [],
                    },
                    "elapsed_sec": 0.3,
                }

        class InlineMeetingNoteJobService(MeetingNoteJobService):
            def _start_background_job(self, context) -> None:
                self._run_job(context)

        with tempfile.TemporaryDirectory(prefix="meeting-note-service-") as temp_dir:
            project_root = Path(temp_dir)
            (project_root / "src" / "prompts").mkdir(parents=True, exist_ok=True)
            (project_root / "src" / "prompts" / "summary_ko.txt").write_text(
                "회의명: {meeting_title}\n{transcript}",
                encoding="utf-8",
            )
            (project_root / ".env").write_text(
                "\n".join(
                    [
                        "WORK_ROOT=./work",
                        "OUTPUT_ROOT=./output",
                        "LOG_ROOT=./logs",
                        "INPUT_ROOT=./input",
                        "DB_URL=sqlite:///./work/app.sqlite3",
                        "SUMMARY_PROVIDER=mock",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            audio_path = project_root / "input-source.m4a"
            audio_path.write_bytes(b"dummy")

            service = InlineMeetingNoteJobService(
                project_root=project_root,
                feature_client=FakeFeatureClient(),
            )
            submitted = service.submit_path_job(audio_path=audio_path, meeting_title="회의")

            output_dir = project_root / "output" / submitted.job_id
            self.assertTrue((output_dir / "transcript_diarized.json").exists())
            self.assertTrue((output_dir / "summary.json").exists())
            self.assertTrue((output_dir / "meeting_notes.txt").exists())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
