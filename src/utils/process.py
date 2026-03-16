from __future__ import annotations

from logging import Logger
from pathlib import Path
import subprocess

from src.utils.errors import StageError


def run_templated_command(
    *,
    stage_name: str,
    command_template: str,
    replacements: dict[str, str],
    cwd: Path,
    logger: Logger,
) -> None:
    if not command_template.strip():
        raise StageError(stage_name, f"{stage_name} stage command is not configured.")

    command = command_template.format(**replacements)
    logger.info("%s stage external command started.", stage_name)
    completed = subprocess.run(
        command,
        shell=True,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else "external command failed"
        raise StageError(stage_name, stderr)
