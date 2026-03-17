from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.bootstrap import JobRequest, create_job_context
from src.services.summarization import run_summary
from src.services.transcription import run_transcription


class FeatureServicesTest(unittest.TestCase):
    def test_transcription_service_runs_in_mock_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            audio_path = root / "meeting.wav"
            audio_path.write_bytes(b"RIFFtest")

            context = create_job_context(
                JobRequest(
                    source_path=audio_path,
                    meeting_title="mock transcribe",
                    pipeline_mode="mock",
                ),
                project_root=root,
            )

            result = run_transcription(context)

            self.assertTrue(result.preprocessed_audio_path.exists())
            self.assertTrue(result.asr_json_path.exists())
            self.assertTrue(result.align_json_path.exists())
            self.assertEqual(result.asr_result.provider, "mock")
            self.assertEqual(result.align_result.provider, "mock")

    def test_summary_service_can_run_from_transcript_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            transcript_path = root / "transcript.json"
            transcript_path.write_text(
                json.dumps(
                    {
                        "meeting_title": "summary test",
                        "provider": "test",
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
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            context = create_job_context(
                JobRequest(
                    source_path=transcript_path,
                    meeting_title="summary test",
                    pipeline_mode="mock",
                ),
                project_root=root,
            )

            result = run_summary(context, transcript_path=transcript_path)

            self.assertTrue(result.transcript_json_path.exists())
            self.assertTrue(result.summary_json_path.exists())
            payload = json.loads(result.summary_json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["provider"], "mock")
            self.assertEqual(payload["meeting_title"], "summary test")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
