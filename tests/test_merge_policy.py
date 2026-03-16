from __future__ import annotations

import unittest

from src.config import AppConfig
from src.schemas.align import AlignResult, AlignedSegment, AlignedWord
from src.schemas.diarization import DiarizationResult, SpeakerTurn
from src.stages import merge


class MergePolicyTest(unittest.TestCase):
    def test_assigns_speakers_and_normalizes_labels(self) -> None:
        align_result = AlignResult(
            provider="test",
            model="align",
            segments=[
                AlignedSegment(
                    text="안녕하세요 모두",
                    start_sec=0.0,
                    end_sec=2.0,
                    words=[
                        AlignedWord(text="안녕하세요", start_sec=0.0, end_sec=1.0),
                        AlignedWord(text="모두", start_sec=1.0, end_sec=2.0),
                    ],
                ),
                AlignedSegment(
                    text="일정 공유",
                    start_sec=2.0,
                    end_sec=4.0,
                    words=[
                        AlignedWord(text="일정", start_sec=2.0, end_sec=3.0),
                        AlignedWord(text="공유", start_sec=3.0, end_sec=4.0),
                    ],
                ),
            ],
        )
        diarization_result = DiarizationResult(
            provider="test",
            model="diarize",
            speakers=[
                SpeakerTurn(speaker_label="speaker_0", start_sec=0.0, end_sec=2.1),
                SpeakerTurn(speaker_label="speaker_1", start_sec=2.1, end_sec=4.0),
            ],
        )
        config = AppConfig(
            project_root=__import__("pathlib").Path(".").resolve(),
            pipeline_mode="mock",
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
        context = type("Context", (), {"config": config, "backchannel_mode": "keep"})

        segments = merge._merge_words_with_speakers(context, align_result, diarization_result)

        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].speaker_label, "화자 A")
        self.assertEqual(segments[1].speaker_label, "화자 B")
        self.assertTrue(segments[0].line.startswith("[00:00:00] 화자 A:"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
