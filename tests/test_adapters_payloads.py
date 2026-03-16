from __future__ import annotations

import unittest

from src.adapters.pyannote_diarize import annotation_to_turns, build_rttm_lines
from src.adapters.qwen_align import build_align_payload
from src.adapters.qwen_asr import build_asr_payload


class AdapterPayloadTest(unittest.TestCase):
    def test_build_asr_payload_filters_empty_segments(self) -> None:
        payload = build_asr_payload(
            model_name="Qwen/Qwen3-ASR-1.7B",
            chunk_results=[
                {"text": "안녕하세요", "language": "Korean", "start_sec": 0.0, "end_sec": 10.0},
                {"text": " ", "language": "Korean", "start_sec": 10.0, "end_sec": 20.0},
            ],
        )
        self.assertEqual(payload["language"], "Korean")
        self.assertEqual(len(payload["segments"]), 1)
        self.assertEqual(payload["segments"][0]["text"], "안녕하세요")

    def test_build_align_payload_wraps_segments(self) -> None:
        payload = build_align_payload(
            model_name="Qwen/Qwen3-ForcedAligner-0.6B",
            aligned_segments=[{"text": "회의 시작", "start_sec": 0.0, "end_sec": 1.0, "words": []}],
        )
        self.assertEqual(payload["provider"], "qwen_forced_aligner")
        self.assertEqual(payload["segments"][0]["text"], "회의 시작")

    def test_annotation_to_turns_and_rttm(self) -> None:
        class Segment:
            def __init__(self, start: float, end: float):
                self.start = start
                self.end = end

        class Annotation:
            def itertracks(self, yield_label: bool = False):
                yield Segment(1.2, 2.4), "track_0", "speaker_1"
                yield Segment(0.1, 1.0), "track_1", "speaker_0"

        turns = annotation_to_turns(Annotation())
        self.assertEqual(turns[0]["speaker_label"], "speaker_0")
        self.assertIn("speaker_1", build_rttm_lines(turns))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
