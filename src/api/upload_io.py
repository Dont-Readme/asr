from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import UploadFile


def save_upload_to_temp(project_root: Path, upload: "UploadFile", *, prefix: str) -> Path:
    temp_root = (project_root / ".api_uploads").resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.filename or "").suffix or ".bin"
    target_path = temp_root / f"{prefix}-{uuid4().hex}{suffix}"
    _write_upload(upload, target_path)
    return target_path


def save_upload_to_input_root(input_root: Path, upload: "UploadFile", *, prefix: str) -> Path:
    input_root.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.filename or "").suffix or ".bin"
    target_path = input_root / f"{prefix}-{uuid4().hex}{suffix}"
    _write_upload(upload, target_path)
    return target_path


def write_bytes_to_input_root(input_root: Path, *, file_name: str, content: bytes, prefix: str) -> Path:
    input_root.mkdir(parents=True, exist_ok=True)
    suffix = Path(file_name).suffix or ".bin"
    target_path = input_root / f"{prefix}-{uuid4().hex}{suffix}"
    target_path.write_bytes(content)
    return target_path


def delete_file_quietly(path: Path | None) -> None:
    if path is None:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return


def build_temp_wave_path(prefix: str = "audio") -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix=f"{prefix}-")).resolve()
    return temp_dir / "audio_16k_mono.wav"


def cleanup_temp_wave(path: Path | None) -> None:
    if path is None:
        return
    try:
        shutil.rmtree(path.parent, ignore_errors=True)
    except OSError:
        return


def _write_upload(upload: "UploadFile", target_path: Path) -> None:
    upload.file.seek(0)
    with target_path.open("wb") as file_pointer:
        shutil.copyfileobj(upload.file, file_pointer)
    upload.file.seek(0)
