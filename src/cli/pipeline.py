from __future__ import annotations

import argparse
import sys

from src.cli.common import add_backchannel_argument, add_common_job_arguments, create_context_from_args
from src.services.pipeline import run_pipeline_job
from src.utils.errors import PipelineError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ASR meeting pipeline CLI")
    add_common_job_arguments(parser, source_label="오디오")
    add_backchannel_argument(parser)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    context = create_context_from_args(args)

    try:
        result = run_pipeline_job(context)
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

