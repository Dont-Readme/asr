from __future__ import annotations

import json

from src.pipeline.job_context import JobContext
from src.schemas.align import AlignResult, AlignedSegment, AlignedWord
from src.schemas.asr import AsrResult
from src.utils.errors import StageError
from src.utils.process import run_templated_command


def run(context: JobContext) -> AlignResult:
    if context.config.pipeline_mode == "mock":
        asr_result = AsrResult.from_dict(json.loads(context.asr_json_path.read_text(encoding="utf-8")))
        result = _build_mock_align_result(context, asr_result)
        context.align_json_path.write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return result

    run_templated_command(
        stage_name="ALIGN",
        command_template=context.config.align_command,
        replacements={
            "audio_path": str(context.preprocessed_audio_path),
            "input_json": str(context.asr_json_path),
            "output_path": str(context.align_json_path),
            "output_dir": str(context.work_dir),
        },
        cwd=context.config.project_root,
        logger=context.logger,
    )
    if not context.align_json_path.exists():
        raise StageError("ALIGN", "ALIGN stage did not create align.json")

    return AlignResult.from_dict(json.loads(context.align_json_path.read_text(encoding="utf-8")))


def _build_mock_align_result(context: JobContext, asr_result: AsrResult) -> AlignResult:
    aligned_segments: list[AlignedSegment] = []
    for segment in asr_result.segments:
        words = segment.text.split()
        if not words:
            continue
        duration = max(segment.end_sec - segment.start_sec, 0.1)
        slice_size = duration / len(words)
        aligned_words = [
            AlignedWord(
                text=word,
                start_sec=segment.start_sec + index * slice_size,
                end_sec=segment.start_sec + (index + 1) * slice_size,
            )
            for index, word in enumerate(words)
        ]
        aligned_segments.append(
            AlignedSegment(
                text=segment.text,
                start_sec=segment.start_sec,
                end_sec=segment.end_sec,
                words=aligned_words,
            )
        )
    return AlignResult(
        provider="mock",
        model=context.config.align_model,
        segments=aligned_segments,
    )
