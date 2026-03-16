from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from src.db.base import initialize_database, resolve_sqlite_path
from src.db.models import JobStage, JobStatus, TranscriptSegmentRecord
from src.utils.time import utcnow_iso


class SqliteJobRepository:
    def __init__(self, db_url: str, project_root: Path):
        self.db_path = resolve_sqlite_path(db_url, project_root)
        initialize_database(self.db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def create_job(
        self,
        *,
        job_id: str,
        input_path: Path,
        meeting_title: str,
        language: str,
        work_dir: Path,
        output_dir: Path,
        log_path: Path,
    ) -> None:
        timestamp = utcnow_iso()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO meeting_job (
                    id, status, current_stage, input_path, meeting_title, language,
                    work_dir, output_dir, log_path, error_stage, error_message,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    JobStatus.PENDING.value,
                    None,
                    str(input_path),
                    meeting_title,
                    language,
                    str(work_dir),
                    str(output_dir),
                    str(log_path),
                    None,
                    None,
                    timestamp,
                    timestamp,
                ),
            )

    def update_job_status(
        self,
        job_id: str,
        *,
        status: JobStatus,
        current_stage: JobStage | None = None,
        error_stage: str | None = None,
        error_message: str | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE meeting_job
                SET status = ?,
                    current_stage = ?,
                    error_stage = ?,
                    error_message = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    status.value,
                    current_stage.value if current_stage else None,
                    error_stage,
                    error_message,
                    utcnow_iso(),
                    job_id,
                ),
            )

    def replace_transcript_segments(self, job_id: str, segments: list[TranscriptSegmentRecord]) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM transcript_segment WHERE job_id = ?", (job_id,))
            connection.executemany(
                """
                INSERT INTO transcript_segment (
                    job_id, speaker_label, start_ms, end_ms, text, words_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        job_id,
                        segment.speaker_label,
                        segment.start_ms,
                        segment.end_ms,
                        segment.text,
                        segment.words_json,
                    )
                    for segment in segments
                ],
            )

    def upsert_summary(self, job_id: str, summary_json: dict) -> None:
        payload = json.dumps(summary_json, ensure_ascii=False, indent=2)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO summary_result (job_id, summary_json, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(job_id)
                DO UPDATE SET summary_json = excluded.summary_json, created_at = excluded.created_at
                """,
                (job_id, payload, utcnow_iso()),
            )

    def register_artifact(self, job_id: str, file_type: str, path: Path, sha256: str | None = None) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO exported_file (job_id, file_type, path, sha256, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (job_id, file_type, str(path), sha256, utcnow_iso()),
            )
