from __future__ import annotations

import argparse
from pathlib import Path

from src.bootstrap import JobRequest, create_job_context


def add_common_job_arguments(parser: argparse.ArgumentParser, *, source_label: str) -> None:
    parser.add_argument("source_path", help=f"입력 {source_label} 파일 경로")
    parser.add_argument("--meeting-title", default=None, help="회의 제목")
    parser.add_argument("--language", default="ko", help="회의 언어")
    parser.add_argument("--output-root", default=None, help="output 루트 override")
    parser.add_argument("--work-root", default=None, help="work 루트 override")
    parser.add_argument("--log-root", default=None, help="log 루트 override")
    parser.add_argument(
        "--pipeline-mode",
        choices=["production", "mock"],
        default=None,
        help="mock 모드는 더미 provider를 사용",
    )
    parser.add_argument("--overwrite", action="store_true", help="같은 회의명 기준 고정 job id 재사용")


def add_backchannel_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--backchannel-mode",
        choices=["keep", "drop", "tag"],
        default=None,
        help="추임새 처리 방식",
    )


def build_job_request(args: argparse.Namespace) -> JobRequest:
    return JobRequest(
        source_path=Path(args.source_path),
        meeting_title=getattr(args, "meeting_title", None),
        language=getattr(args, "language", "ko"),
        output_root=Path(args.output_root).resolve() if getattr(args, "output_root", None) else None,
        work_root=Path(args.work_root).resolve() if getattr(args, "work_root", None) else None,
        log_root=Path(args.log_root).resolve() if getattr(args, "log_root", None) else None,
        backchannel_mode=getattr(args, "backchannel_mode", None),
        pipeline_mode=getattr(args, "pipeline_mode", None),
        overwrite=getattr(args, "overwrite", False),
    )


def create_context_from_args(args: argparse.Namespace):
    return create_job_context(build_job_request(args))

