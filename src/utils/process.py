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
        stderr_lines = completed.stderr.strip().splitlines() if completed.stderr.strip() else []
        stdout_lines = completed.stdout.strip().splitlines() if completed.stdout.strip() else []
        logger.error("%s stage external command failed with code %s", stage_name, completed.returncode)
        if stdout_lines:
            logger.error("%s stage stdout tail:\n%s", stage_name, "\n".join(stdout_lines[-20:]))
        if stderr_lines:
            logger.error("%s stage stderr tail:\n%s", stage_name, "\n".join(stderr_lines[-20:]))

        if stderr_lines:
            message = "\n".join(stderr_lines[-20:])
        elif stdout_lines:
            message = "\n".join(stdout_lines[-20:])
        else:
            message = "external command failed"
        raise StageError(stage_name, message)
