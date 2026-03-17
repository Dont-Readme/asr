from __future__ import annotations

from src.pipeline.job_context import JobContext
from src.pipeline.orchestrator import run_pipeline


def run_pipeline_job(context: JobContext) -> dict[str, str]:
    return run_pipeline(context)

