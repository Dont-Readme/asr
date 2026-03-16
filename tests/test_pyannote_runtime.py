from __future__ import annotations

import unittest

from src.adapters.pyannote_diarize import validate_pyannote_runtime


class PyannoteRuntimeTest(unittest.TestCase):
    def test_community_1_requires_major_4(self) -> None:
        with self.assertRaises(RuntimeError):
            validate_pyannote_runtime("3.4.0", "pyannote/speaker-diarization-community-1")

    def test_legacy_model_allows_major_3(self) -> None:
        validate_pyannote_runtime("3.4.1", "pyannote/speaker-diarization-3.1")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
