from __future__ import annotations

import shutil

from src.pipeline.job_context import JobContext
from src.utils.errors import StageError
from src.utils.ffmpeg import convert_audio


def run(context: JobContext):
    if not context.input_path.exists():
        raise StageError("PREPROCESS", f"입력 파일이 없습니다: {context.input_path}")

    if context.config.pipeline_mode == "mock" and context.input_path.suffix.lower() == ".wav":
        shutil.copyfile(context.input_path, context.preprocessed_audio_path)
        context.artifacts["preprocessed_audio"] = context.preprocessed_audio_path
        return context.preprocessed_audio_path

    convert_audio(
        input_path=context.input_path,
        output_path=context.preprocessed_audio_path,
        sample_rate=context.config.audio_target_sr,
        channels=context.config.audio_target_channels,
    )
    context.artifacts["preprocessed_audio"] = context.preprocessed_audio_path
    return context.preprocessed_audio_path
