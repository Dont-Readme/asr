from __future__ import annotations

import os
import time

from fastapi import FastAPI, HTTPException

from src.api.models import RuntimeHealthResponse, SummaryPayloadRequest, SummaryPayloadResponse
from src.bootstrap import default_project_root, load_app_config
from src.schemas.transcript import TranscriptResult
from src.services.task_runner import TaskRunner
from src.services.summary_generation import summarize_transcript
from src.utils.errors import PipelineError
from src.utils.time import utcnow_iso


def create_app(summary_fn=summarize_transcript, task_runner: TaskRunner | None = None) -> FastAPI:
    project_root = default_project_root()
    config = load_app_config(project_root=project_root)
    loaded_at = utcnow_iso()
    process_id = os.getpid()
    resolved_runner = task_runner or TaskRunner(
        name="summarize",
        workers=config.summarize_max_concurrency,
    )

    app = FastAPI(title="ASR Summary API", version="0.2.0")
    app.state.task_runner = resolved_runner

    @app.get("/health", response_model=RuntimeHealthResponse)
    def health() -> RuntimeHealthResponse:
        return RuntimeHealthResponse(
            status="ready",
            loaded_at=loaded_at,
            process_id=process_id,
            device="external",
            models={"summary": config.summary_model or config.summary_provider},
        )

    @app.post("/summaries", response_model=SummaryPayloadResponse)
    def summarize(request: SummaryPayloadRequest) -> SummaryPayloadResponse:
        started_at = time.perf_counter()
        try:
            def _execute():
                transcript = TranscriptResult.from_dict(
                    {
                        "meeting_title": request.meeting_title,
                        "provider": request.transcript.get("provider", "api_payload"),
                        "segments": request.transcript.get("segments", []),
                    }
                )
                return summary_fn(
                    config,
                    meeting_title=request.meeting_title,
                    transcript=transcript,
                )

            summary = resolved_runner.submit(
                _execute,
            )
        except (PipelineError, RuntimeError, ValueError, KeyError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return SummaryPayloadResponse(
            summary=summary.to_dict(),
            elapsed_sec=round(time.perf_counter() - started_at, 3),
        )

    return app
