from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.config import load_config
from src.db.repo import SqliteJobRepository
from src.pipeline.job_context import JobContext
from src.pipeline.orchestrator import run_pipeline
from src.utils.errors import PipelineError
from src.utils.logging import setup_job_logger
from src.utils.paths import build_job_dirs, build_job_id, derive_meeting_title, ensure_project_roots


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ASR meeting pipeline bootstrap CLI")
    parser.add_argument("audio_path", help="입력 오디오 파일 경로")
    parser.add_argument("--meeting-title", default=None, help="회의 제목")
    parser.add_argument("--language", default="ko", help="회의 언어")
    parser.add_argument("--output-root", default=None, help="output 루트 override")
    parser.add_argument("--work-root", default=None, help="work 루트 override")
    parser.add_argument("--log-root", default=None, help="log 루트 override")
    parser.add_argument(
        "--backchannel-mode",
        choices=["keep", "drop", "tag"],
        default=None,
        help="추임새 처리 방식",
    )
    parser.add_argument(
        "--pipeline-mode",
        choices=["production", "mock"],
        default=None,
        help="mock 모드는 더미 ASR/align/diarize/summary를 사용",
    )
    parser.add_argument("--overwrite", action="store_true", help="같은 회의명 기준 고정 job id 재사용")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = Path(__file__).resolve().parent
    config = load_config(project_root).with_overrides(
        pipeline_mode=args.pipeline_mode,
        work_root=Path(args.work_root).resolve() if args.work_root else None,
        output_root=Path(args.output_root).resolve() if args.output_root else None,
        log_root=Path(args.log_root).resolve() if args.log_root else None,
        backchannel_mode=args.backchannel_mode,
    )
    ensure_project_roots(config)

    input_path = Path(args.audio_path).expanduser().resolve()
    meeting_title = derive_meeting_title(input_path, args.meeting_title)
    job_id = build_job_id(meeting_title, overwrite=args.overwrite)
    work_dir, output_dir, log_path = build_job_dirs(config, job_id)
    logger = setup_job_logger(job_id, log_path)
    repo = SqliteJobRepository(config.db_url, project_root)

    context = JobContext(
        job_id=job_id,
        input_path=input_path,
        meeting_title=meeting_title,
        language=args.language,
        config=config,
        work_dir=work_dir,
        output_dir=output_dir,
        log_path=log_path,
        logger=logger,
        repo=repo,
        backchannel_mode=config.backchannel_mode,
        overwrite=args.overwrite,
    )
    repo.create_job(
        job_id=job_id,
        input_path=input_path,
        meeting_title=meeting_title,
        language=args.language,
        work_dir=work_dir,
        output_dir=output_dir,
        log_path=log_path,
    )

    try:
        result = run_pipeline(context)
    except PipelineError as error:
        print(str(error), file=sys.stderr)
        return 1

    print(f"job_id={result['job_id']}")
    print(f"transcript={result['transcript_path']}")
    print(f"summary={result['summary_path']}")
    print(f"meeting_notes={result['meeting_notes_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
