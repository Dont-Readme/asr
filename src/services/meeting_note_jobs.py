from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from src.bootstrap import JobRequest, create_job_context, default_project_root, load_app_config
from src.clients.feature_api_client import FeatureApiClient
from src.db.models import JobStage, JobStatus
from src.pipeline.job_context import JobContext
from src.schemas.summary import MeetingSummary
from src.services.persistence import persist_summary_result, persist_transcript_records
from src.services.task_runner import TaskRunner
from src.stages import export, merge
from src.utils.errors import StageError
from src.utils.paths import compute_sha256


@dataclass(slots=True)
class SubmittedMeetingNoteJob:
    job_id: str
    meeting_title: str


class MeetingNoteJobService:
    def __init__(self, *, project_root: Path | None = None, feature_client: FeatureApiClient | None = None) -> None:
        self.project_root = (project_root or default_project_root()).resolve()
        self.config = load_app_config(project_root=self.project_root)
        self.feature_client = feature_client or FeatureApiClient(self.config)
        self.job_runner = TaskRunner(
            name="meeting-note-jobs",
            workers=self.config.meeting_job_workers,
        )

    def submit_path_job(
        self,
        *,
        audio_path: Path,
        meeting_title: str | None = None,
        language: str = "ko",
        output_root: Path | None = None,
        work_root: Path | None = None,
        log_root: Path | None = None,
        pipeline_mode: str | None = None,
        overwrite: bool = False,
    ) -> SubmittedMeetingNoteJob:
        context = create_job_context(
            JobRequest(
                source_path=audio_path,
                meeting_title=meeting_title,
                language=language,
                output_root=output_root,
                work_root=work_root,
                log_root=log_root,
                pipeline_mode=pipeline_mode,
                overwrite=overwrite,
            ),
            project_root=self.project_root,
        )
        self._start_background_job(context)
        return SubmittedMeetingNoteJob(job_id=context.job_id, meeting_title=context.meeting_title)

    def _start_background_job(self, context: JobContext) -> None:
        self.job_runner.enqueue(
            lambda: self._run_job(context),
        )

    def _run_job(self, context: JobContext) -> None:
        context.repo.update_job_status(context.job_id, status=JobStatus.RUNNING)
        context.logger.info("Meeting-note job started.")
        try:
            transcription_payload = self._run_transcription_api(context)
            diarization_payload = self._run_diarization_api(context)
            transcript_result = self._run_merge(context, transcription_payload, diarization_payload)
            summary_result = self._run_summary_api(context, transcript_result.to_dict())
            self._run_export(context, summary_result)
            context.repo.update_job_status(
                context.job_id,
                status=JobStatus.DONE,
                current_stage=JobStage.EXPORT,
            )
            context.logger.info("Meeting-note job completed.")
        except StageError as error:
            context.logger.exception("Meeting-note job failed at %s", error.stage)
            context.repo.update_job_status(
                context.job_id,
                status=JobStatus.FAILED,
                current_stage=None,
                error_stage=error.stage,
                error_message=error.message,
            )
        except Exception as error:  # pragma: no cover - safety net
            context.logger.exception("Meeting-note job failed unexpectedly")
            context.repo.update_job_status(
                context.job_id,
                status=JobStatus.FAILED,
                current_stage=None,
                error_stage="UNKNOWN",
                error_message=str(error),
            )

    def _run_transcription_api(self, context: JobContext) -> dict:
        context.repo.update_job_status(context.job_id, status=JobStatus.RUNNING, current_stage=JobStage.ASR)
        context.logger.info("Calling meeting transcription API.")
        payload = self.feature_client.transcribe_meeting_by_path(
            audio_path=str(context.input_path),
            language=context.language,
        )
        asr_payload = payload.get("asr")
        align_payload = payload.get("align")
        if not isinstance(asr_payload, dict) or not isinstance(align_payload, dict):
            raise StageError("ASR", "meeting transcription API 응답에 asr/align payload가 없습니다.")

        context.asr_json_path.write_text(json.dumps(asr_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        context.align_json_path.write_text(json.dumps(align_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        context.repo.register_artifact(
            context.job_id,
            "asr_json",
            context.asr_json_path,
            compute_sha256(context.asr_json_path),
        )
        context.repo.update_job_status(context.job_id, status=JobStatus.RUNNING, current_stage=JobStage.ALIGN)
        context.repo.register_artifact(
            context.job_id,
            "align_json",
            context.align_json_path,
            compute_sha256(context.align_json_path),
        )
        return payload

    def _run_diarization_api(self, context: JobContext) -> dict:
        context.repo.update_job_status(context.job_id, status=JobStatus.RUNNING, current_stage=JobStage.DIARIZE)
        context.logger.info("Calling diarization API.")
        payload = self.feature_client.diarize_by_path(audio_path=str(context.input_path))
        diarization = payload.get("diarization")
        rttm = payload.get("rttm")
        if not isinstance(diarization, dict) or not isinstance(rttm, str):
            raise StageError("DIARIZE", "diarization API 응답에 diarization/rttm payload가 없습니다.")

        context.diarization_json_path.write_text(
            json.dumps(diarization, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        context.diarization_rttm_path.write_text(rttm, encoding="utf-8")
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
        return payload

    def _run_merge(self, context: JobContext, transcription_payload: dict, diarization_payload: dict):
        del transcription_payload, diarization_payload
        context.repo.update_job_status(context.job_id, status=JobStatus.RUNNING, current_stage=JobStage.MERGE)
        context.logger.info("Merging align and diarization results.")
        transcript = merge.run(context)
        persist_transcript_records(context, transcript)
        return transcript

    def _run_summary_api(self, context: JobContext, transcript_payload: dict) -> MeetingSummary:
        context.repo.update_job_status(context.job_id, status=JobStatus.RUNNING, current_stage=JobStage.SUMMARIZE)
        context.logger.info("Calling summary API.")
        payload = self.feature_client.summarize_transcript(
            meeting_title=context.meeting_title,
            transcript=transcript_payload,
        )
        summary_payload = payload.get("summary")
        if not isinstance(summary_payload, dict):
            raise StageError("SUMMARIZE", "summary API 응답에 summary payload가 없습니다.")
        summary = MeetingSummary.from_dict(summary_payload)
        context.summary_json_path.write_text(
            json.dumps(summary.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        context.repo.register_artifact(
            context.job_id,
            "summary_json",
            context.summary_json_path,
            compute_sha256(context.summary_json_path),
        )
        persist_summary_result(context, summary)
        return summary

    def _run_export(self, context: JobContext, summary_result: MeetingSummary) -> Path:
        del summary_result
        context.repo.update_job_status(context.job_id, status=JobStatus.RUNNING, current_stage=JobStage.EXPORT)
        context.logger.info("Rendering meeting notes text.")
        return export.run(context)
