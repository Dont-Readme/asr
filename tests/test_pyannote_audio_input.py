from __future__ import annotations

import tempfile
import unittest
import wave
from pathlib import Path

from src.adapters.pyannote_diarize import load_audio_for_pyannote


class PyannoteAudioInputTest(unittest.TestCase):
    def test_load_audio_for_pyannote_returns_waveform_mapping(self) -> None:
        try:
            import torchaudio  # noqa: F401
        except ImportError:
            self.skipTest("torchaudio is not installed in local test env")

        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_path = Path(tmp_dir) / "sample.wav"
            with wave.open(str(audio_path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(b"\x00\x00" * 1600)

            payload = load_audio_for_pyannote(audio_path)

            self.assertEqual(payload["sample_rate"], 16000)
            self.assertEqual(payload["uri"], "sample")
            self.assertEqual(payload["waveform"].shape[0], 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
