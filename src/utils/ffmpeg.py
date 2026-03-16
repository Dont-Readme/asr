from __future__ import annotations

from pathlib import Path
import subprocess

from src.utils.errors import StageError


def build_ffmpeg_command(
    input_path: Path,
    output_path: Path,
    sample_rate: int,
    channels: int,
) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-ar",
        str(sample_rate),
        "-ac",
        str(channels),
        str(output_path),
    ]


def convert_audio(
    input_path: Path,
    output_path: Path,
    sample_rate: int,
    channels: int,
) -> None:
    command = build_ffmpeg_command(input_path, output_path, sample_rate, channels)
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as error:
        raise StageError("PREPROCESS", "ffmpeg가 설치되어 있지 않습니다.") from error

    if completed.returncode != 0:
        stderr = completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else "unknown ffmpeg error"
        raise StageError("PREPROCESS", f"ffmpeg 변환 실패: {stderr}")
