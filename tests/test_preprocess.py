from __future__ import annotations

import logging
import tempfile
import unittest
from pathlib import Path

from src.config import AppConfig
from src.pipeline.job_context import JobContext
from src.stages import preprocess
from src.db.repo import SqliteJobRepository
from src.utils.ffmpeg import build_ffmpeg_command


class BuildFfmpegCommandTest(unittest.TestCase):
    def test_builds_expected_ffmpeg_args(self) -> None:
        command = build_ffmpeg_command(
            input_path=Path("/tmp/input.m4a"),
            output_path=Path("/tmp/output.wav"),
            sample_rate=16000,
            channels=1,
        )
        self.assertEqual(
            command,
            [
                "ffmpeg",
                "-y",
                "-i",
                "/tmp/input.m4a",
                "-ar",
                "16000",
                "-ac",
                "1",
                "/tmp/output.wav",
            ],
        )

    def test_mock_mode_copies_existing_wav_without_ffmpeg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            input_path = root / "input.wav"
            input_path.write_bytes(b"RIFFtest")

            config = AppConfig(
                project_root=root,
                pipeline_mode="mock",
                work_root=root / "work",
                output_root=root / "output",
                log_root=root / "logs",
                input_root=root / "input",
                device="cpu",
                asr_model="asr",
                align_model="align",
                diarization_model="diarize",
                asr_command="",
                align_command="",
                diarization_command="",
                hf_home=root / ".hf_cache",
                huggingface_hub_token="",
                db_url="sqlite:///./work/app.sqlite3",
                summary_provider="mock",
                summary_base_url="http://127.0.0.1:8000",
                summary_endpoint_path="/generate",
                summary_api_key="",
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
            config.work_root.mkdir(parents=True, exist_ok=True)
            config.output_root.mkdir(parents=True, exist_ok=True)
            config.log_root.mkdir(parents=True, exist_ok=True)
            repo = SqliteJobRepository(config.db_url, root)
            work_dir = root / "work" / "job"
            output_dir = root / "output" / "job"
            work_dir.mkdir(parents=True, exist_ok=True)
            output_dir.mkdir(parents=True, exist_ok=True)

            context = JobContext(
                job_id="job",
                input_path=input_path,
                meeting_title="테스트",
                language="ko",
                config=config,
                work_dir=work_dir,
                output_dir=output_dir,
                log_path=root / "logs" / "job.log",
                logger=logging.getLogger("test.preprocess"),
                repo=repo,
                backchannel_mode="keep",
            )

            output_path = preprocess.run(context)

            self.assertTrue(output_path.exists())
            self.assertEqual(output_path.read_bytes(), b"RIFFtest")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
