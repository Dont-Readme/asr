from __future__ import annotations

from pathlib import Path
import sqlite3


def resolve_sqlite_path(db_url: str, project_root: Path) -> Path:
    prefix = "sqlite:///"
    if not db_url.startswith(prefix):
        raise ValueError("Only sqlite:/// URLs are supported in this bootstrap.")
    raw_path = db_url[len(prefix) :]
    path = Path(raw_path)
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()


def initialize_database(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS meeting_job (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                current_stage TEXT,
                input_path TEXT NOT NULL,
                meeting_title TEXT NOT NULL,
                language TEXT,
                work_dir TEXT NOT NULL,
                output_dir TEXT NOT NULL,
                log_path TEXT NOT NULL,
                error_stage TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS transcript_segment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                speaker_label TEXT NOT NULL,
                start_ms INTEGER NOT NULL,
                end_ms INTEGER NOT NULL,
                text TEXT NOT NULL,
                words_json TEXT,
                FOREIGN KEY(job_id) REFERENCES meeting_job(id)
            );

            CREATE TABLE IF NOT EXISTS summary_result (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL UNIQUE,
                summary_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES meeting_job(id)
            );

            CREATE TABLE IF NOT EXISTS exported_file (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                file_type TEXT NOT NULL,
                path TEXT NOT NULL,
                sha256 TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES meeting_job(id)
            );
            """
        )
