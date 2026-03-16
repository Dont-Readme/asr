from __future__ import annotations

import unittest

from src.adapters.pyannote_diarize import build_pipeline_load_kwargs


class PyannoteAdapterCompatTest(unittest.TestCase):
    def test_prefers_token_when_supported(self) -> None:
        def loader(checkpoint, token=None):  # noqa: ANN001
            return checkpoint, token

        kwargs = build_pipeline_load_kwargs(loader, "hf_xxx")
        self.assertEqual(kwargs, {"token": "hf_xxx"})

    def test_falls_back_to_use_auth_token(self) -> None:
        def loader(checkpoint, use_auth_token=None):  # noqa: ANN001
            return checkpoint, use_auth_token

        kwargs = build_pipeline_load_kwargs(loader, "hf_xxx")
        self.assertEqual(kwargs, {"use_auth_token": "hf_xxx"})

    def test_returns_empty_when_no_supported_parameter(self) -> None:
        def loader(checkpoint):  # noqa: ANN001
            return checkpoint

        kwargs = build_pipeline_load_kwargs(loader, "hf_xxx")
        self.assertEqual(kwargs, {})


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
