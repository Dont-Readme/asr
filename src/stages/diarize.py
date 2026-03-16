from __future__ import annotations

import json

from src.pipeline.job_context import JobContext
from src.schemas.align import AlignResult
from src.schemas.diarization import DiarizationResult, SpeakerTurn
from src.utils.errors import StageError
from src.utils.process import run_templated_command


def run(context: JobContext) -> DiarizationResult:
    if context.config.pipeline_mode == "mock":
        align_result = AlignResult.from_dict(json.loads(context.align_json_path.read_text(encoding="utf-8")))
        result = _build_mock_diarization_result(context, align_result)
        context.diarization_json_path.write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        context.diarization_rttm_path.write_text(_to_rttm(result), encoding="utf-8")
        return result

    run_templated_command(
        stage_name="DIARIZE",
        command_template=context.config.diarization_command,
        replacements={
            "audio_path": str(context.preprocessed_audio_path),
            "output_path": str(context.diarization_json_path),
            "output_dir": str(context.work_dir),
        },
        cwd=context.config.project_root,
        logger=context.logger,
    )
    if not context.diarization_json_path.exists():
        raise StageError("DIARIZE", "DIARIZE stage did not create diarization.json")

    result = DiarizationResult.from_dict(json.loads(context.diarization_json_path.read_text(encoding="utf-8")))
    if not context.diarization_rttm_path.exists():
        context.diarization_rttm_path.write_text(_to_rttm(result), encoding="utf-8")
    return result


def _build_mock_diarization_result(context: JobContext, align_result: AlignResult) -> DiarizationResult:
    speakers: list[SpeakerTurn] = []
    for index, segment in enumerate(align_result.segments):
        speakers.append(
            SpeakerTurn(
                speaker_label=f"speaker_{index % 2}",
                start_sec=segment.start_sec,
                end_sec=segment.end_sec,
            )
        )
    return DiarizationResult(
        provider="mock",
        model=context.config.diarization_model,
        speakers=speakers,
    )


def _to_rttm(result: DiarizationResult) -> str:
    lines = []
    for turn in result.speakers:
        duration = max(turn.end_sec - turn.start_sec, 0.0)
        lines.append(
            f"SPEAKER meeting 1 {turn.start_sec:.3f} {duration:.3f} <NA> <NA> {turn.speaker_label} <NA> <NA>"
        )
    return "\n".join(lines) + ("\n" if lines else "")
