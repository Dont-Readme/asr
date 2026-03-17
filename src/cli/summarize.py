from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.bootstrap import JobRequest, create_job_context
from src.services.summarization import run_summary
from src.utils.errors import PipelineError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run summarization feature from transcript JSON")
    parser.add_argument("transcript_path", help="화자 포함 transcript JSON 경로")
    parser.add_argument("--meeting-title", required=True, help="회의 제목")
    parser.add_argument("--language", default="ko", help="회의 언어")
    parser.add_argument("--output-root", default=None, help="output 루트 override")
    parser.add_argument("--work-root", default=None, help="work 루트 override")
    parser.add_argument("--log-root", default=None, help="log 루트 override")
    parser.add_argument(
        "--pipeline-mode",
        choices=["production", "mock"],
        default=None,
        help="mock 모드는 더미 summary를 사용",
    )
    parser.add_argument("--overwrite", action="store_true", help="같은 회의명 기준 고정 job id 재사용")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    transcript_path = Path(args.transcript_path)
    context = create_job_context(
        JobRequest(
            source_path=transcript_path,
            meeting_title=args.meeting_title,
            language=args.language,
            output_root=Path(args.output_root).resolve() if args.output_root else None,
            work_root=Path(args.work_root).resolve() if args.work_root else None,
            log_root=Path(args.log_root).resolve() if args.log_root else None,
            pipeline_mode=args.pipeline_mode,
            overwrite=args.overwrite,
        )
    )

    try:
        result = run_summary(context, transcript_path=transcript_path)
    except PipelineError as error:
        print(str(error), file=sys.stderr)
        return 1

    print(f"job_id={context.job_id}")
    print(f"transcript={result.transcript_json_path}")
    print(f"summary={result.summary_json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

