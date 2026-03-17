from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.db.models import JobStage
from src.pipeline.job_context import JobContext
from src.schemas.diarization import DiarizationResult
from src.services.common import mark_feature_done, mark_feature_failed, run_feature_stage
from src.stages import diarize, preprocess
from src.utils.paths import compute_sha256


@dataclass(slots=True)
class DiarizationArtifacts:
    preprocessed_audio_path: Path
    diarization_json_path: Path
    diarization_rttm_path: Path
    result: DiarizationResult


def run_diarization(context: JobContext) -> DiarizationArtifacts:
    try:
        audio_path = run_feature_stage(context, JobStage.PREPROCESS, preprocess.run)
        result = run_feature_stage(context, JobStage.DIARIZE, diarize.run)
        context.repo.register_artifact(
            context.job_id,
            "preprocessed_audio_wav",
            context.preprocessed_audio_path,
            compute_sha256(context.preprocessed_audio_path),
        )
        context.repo.register_artifact(
            context.job_id,
            "diarization_json",
            context.diarization_json_path,
            compute_sha256(context.diarization_json_path),
        )
        context.repo.register_artifact(
            context.job_id,
            "diarization_rttm",
            context.diarization_rttm_path,
            compute_sha256(context.diarization_rttm_path),
        )
        mark_feature_done(context, JobStage.DIARIZE)
        return DiarizationArtifacts(
            preprocessed_audio_path=audio_path,
            diarization_json_path=context.diarization_json_path,
            diarization_rttm_path=context.diarization_rttm_path,
            result=result,
        )
    except Exception as error:
        mark_feature_failed(context, "DIARIZE", error)
        raise
