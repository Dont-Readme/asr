from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re
from uuid import uuid4

from src.config import AppConfig


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_project_roots(config: AppConfig) -> None:
    ensure_directory(config.work_root)
    ensure_directory(config.output_root)
    ensure_directory(config.log_root)
    ensure_directory(config.input_root)
    ensure_directory(config.hf_home)


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE)
    collapsed = re.sub(r"[-\s]+", "-", cleaned.strip())
    return collapsed.lower() or "meeting"


def build_job_id(meeting_title: str, overwrite: bool) -> str:
    prefix = slugify(meeting_title)[:48]
    suffix = "latest" if overwrite else uuid4().hex[:8]
    return f"{prefix}-{suffix}"


def build_job_dirs(config: AppConfig, job_id: str) -> tuple[Path, Path, Path]:
    work_dir = ensure_directory(config.work_root / job_id)
    output_dir = ensure_directory(config.output_root / job_id)
    log_path = config.log_root / f"{job_id}.log"
    ensure_directory(log_path.parent)
    return work_dir, output_dir, log_path


def derive_meeting_title(audio_path: Path, explicit_title: str | None) -> str:
    if explicit_title:
        return explicit_title.strip()
    return audio_path.stem.replace("_", " ").replace("-", " ").strip() or "회의"


def compute_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as file_pointer:
        for chunk in iter(lambda: file_pointer.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
