from __future__ import annotations

from types import SimpleNamespace
import unittest

from src.adapters.pyannote_diarize import LoadedDiarizationRuntime, diarize_with_runtime
from src.adapters.qwen_align import LoadedAlignRuntime, align_with_runtime
from src.adapters.qwen_asr import LoadedAsrRuntime, transcribe_with_runtime


class ResidentRuntimeHelpersTest(unittest.TestCase):
    def test_transcribe_with_runtime_builds_payload(self) -> None:
        class FakeAsrModel:
            def transcribe(self, *, audio, context, language, return_time_stamps):
                self.assertFalse = return_time_stamps  # pragma: no cover - keeps signature realistic
                return [
                    SimpleNamespace(text="안녕하세요", language="Korean"),
                    SimpleNamespace(text="회의를 시작합니다", language="Korean"),
                ]

        runtime = LoadedAsrRuntime(
            model_name="Qwen/Qwen3-ASR-1.7B",
            forced_language="Korean",
            context="",
            chunk_max_seconds=3.0,
            max_batch_size=4,
            model=FakeAsrModel(),
            sample_rate=1,
            normalize_audio_input=lambda path: [0, 1, 2, 3, 4, 5],
            split_audio_into_chunks=lambda wav, sr, max_chunk_sec: [([0, 1], 0.0), ([2, 3], 3.0)],
        )

        payload = transcribe_with_runtime(runtime, audio_path=SimpleNamespace(resolve=lambda: "dummy.wav"))
        self.assertEqual(payload["provider"], "qwen_asr")
        self.assertEqual(len(payload["segments"]), 2)
        self.assertEqual(payload["segments"][0]["start_sec"], 0.0)

    def test_align_with_runtime_uses_segment_offsets(self) -> None:
        class FakeWord:
            def __init__(self, text: str, start_time: float, end_time: float):
                self.text = text
                self.start_time = start_time
                self.end_time = end_time

        class FakeAlignResult:
            def __init__(self, items):
                self.items = items

        class FakeAligner:
            def align(self, *, audio, text, language):
                return [FakeAlignResult([FakeWord(text[0], 0.1, 0.7)])]

        runtime = LoadedAlignRuntime(
            model_name="Qwen/Qwen3-ForcedAligner-0.6B",
            forced_language="Korean",
            max_batch_size=2,
            model=FakeAligner(),
            sample_rate=1,
            normalize_audio_input=lambda path: list(range(10)),
        )

        payload = align_with_runtime(
            runtime,
            audio_path=SimpleNamespace(resolve=lambda: "dummy.wav"),
            asr_payload={"language": "Korean", "segments": [{"text": "회의", "start_sec": 2.0, "end_sec": 4.0}]},
        )
        self.assertEqual(payload["provider"], "qwen_forced_aligner")
        self.assertEqual(payload["segments"][0]["start_sec"], 2.1)
        self.assertEqual(payload["segments"][0]["end_sec"], 2.7)

    def test_diarize_with_runtime_returns_payload_and_rttm(self) -> None:
        class Segment:
            def __init__(self, start: float, end: float):
                self.start = start
                self.end = end

        class Annotation:
            def itertracks(self, yield_label: bool = False):
                yield Segment(0.0, 1.0), "track_a", "speaker_0"

        class FakePipeline:
            def __call__(self, diarization_input, **kwargs):
                return Annotation()

        runtime = LoadedDiarizationRuntime(
            model_name="pyannote/speaker-diarization-community-1",
            pipeline=FakePipeline(),
            default_num_speakers=None,
            default_min_speakers=None,
            default_max_speakers=None,
        )

        original_loader = __import__("src.adapters.pyannote_diarize", fromlist=["load_audio_for_pyannote"]).load_audio_for_pyannote
        try:
            module = __import__("src.adapters.pyannote_diarize", fromlist=["load_audio_for_pyannote"])
            module.load_audio_for_pyannote = lambda audio_path: {
                "waveform": "dummy",
                "sample_rate": 16000,
                "uri": "meeting",
            }
            payload, rttm = diarize_with_runtime(runtime, audio_path=SimpleNamespace(resolve=lambda: "dummy.wav"))
        finally:
            module.load_audio_for_pyannote = original_loader

        self.assertEqual(payload["provider"], "pyannote.audio")
        self.assertEqual(payload["speakers"][0]["speaker_label"], "speaker_0")
        self.assertIn("SPEAKER meeting 1 0.000 1.000", rttm)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
