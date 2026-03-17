from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.db.models import JobStage
from src.pipeline.job_context import JobContext
from src.schemas.align import AlignResult
from src.schemas.asr import AsrResult
from src.services.common import mark_feature_done, mark_feature_failed, run_feature_stage
from src.stages import align, asr, preprocess
from src.utils.paths import compute_sha256


@dataclass(slots=True)
class TranscriptionArtifacts:
    preprocessed_audio_path: Path
    asr_json_path: Path
    align_json_path: Path
    asr_result: AsrResult
    align_result: AlignResult


def run_transcription(context: JobContext) -> TranscriptionArtifacts:
    try:
        audio_path = run_feature_stage(context, JobStage.PREPROCESS, preprocess.run)
        asr_result = run_feature_stage(context, JobStage.ASR, asr.run)
        align_result = run_feature_stage(context, JobStage.ALIGN, align.run)
        context.repo.register_artifact(
            context.job_id,
            "preprocessed_audio_wav",
            context.preprocessed_audio_path,
            compute_sha256(context.preprocessed_audio_path),
        )
        context.repo.register_artifact(
            context.job_id,
            "asr_json",
            context.asr_json_path,
            compute_sha256(context.asr_json_path),
        )
        context.repo.register_artifact(
            context.job_id,
            "align_json",
            context.align_json_path,
            compute_sha256(context.align_json_path),
        )
        mark_feature_done(context, JobStage.ALIGN)
        return TranscriptionArtifacts(
            preprocessed_audio_path=audio_path,
            asr_json_path=context.asr_json_path,
            align_json_path=context.align_json_path,
            asr_result=asr_result,
            align_result=align_result,
        )
    except Exception as error:
        mark_feature_failed(context, "TRANSCRIBE", error)
        raise
