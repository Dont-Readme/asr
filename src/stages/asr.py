from __future__ import annotations

import json

from src.pipeline.job_context import JobContext
from src.schemas.asr import AsrResult, AsrSegment
from src.utils.errors import StageError
from src.utils.process import run_templated_command


def run(context: JobContext) -> AsrResult:
    if context.config.pipeline_mode == "mock":
        result = _build_mock_asr_result(context)
        context.asr_json_path.write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return result

    run_templated_command(
        stage_name="ASR",
        command_template=context.config.asr_command,
        replacements={
            "audio_path": str(context.preprocessed_audio_path),
            "output_path": str(context.asr_json_path),
            "output_dir": str(context.work_dir),
        },
        cwd=context.config.project_root,
        logger=context.logger,
    )
    if not context.asr_json_path.exists():
        raise StageError("ASR", "ASR stage did not create asr.json")

    return AsrResult.from_dict(json.loads(context.asr_json_path.read_text(encoding="utf-8")))


def _build_mock_asr_result(context: JobContext) -> AsrResult:
    segments = [
        AsrSegment(
            text=f"{context.meeting_title}를 시작하겠습니다.",
            start_sec=0.0,
            end_sec=2.4,
        ),
        AsrSegment(
            text="지난주 진행 상황을 공유하고 이번 주 우선순위를 정리하겠습니다.",
            start_sec=2.4,
            end_sec=7.2,
        ),
        AsrSegment(
            text="결정 사항과 후속 작업을 확인하고 마무리하겠습니다.",
            start_sec=7.2,
            end_sec=11.6,
        ),
    ]
    return AsrResult(
        provider="mock",
        model=context.config.asr_model,
        language=context.language,
        segments=segments,
    )
