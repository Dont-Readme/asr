from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.stages import summarize


class SummaryPromptRenderTest(unittest.TestCase):
    def test_render_prompt_keeps_literal_json_braces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            prompt_dir = root / "src" / "prompts"
            prompt_dir.mkdir(parents=True, exist_ok=True)
            prompt_dir.joinpath("summary_ko.txt").write_text(
                '스키마: {"meeting_title":"string"}\n회의명: {meeting_title}\n전사:\n{transcript}\n',
                encoding="utf-8",
            )

            context = type(
                "Context",
                (),
                {
                    "config": type("Config", (), {"project_root": root})(),
                    "meeting_title": "주간 회의",
                },
            )()
            transcript = type(
                "Transcript",
                (),
                {"segments": [type("Segment", (), {"line": "[00:00:00] 화자 A: 안녕하세요"})()]},
            )()

            rendered = summarize._render_prompt(context, transcript)

            self.assertIn('{"meeting_title":"string"}', rendered)
            self.assertIn("회의명: 주간 회의", rendered)
            self.assertIn("[00:00:00] 화자 A: 안녕하세요", rendered)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
