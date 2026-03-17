from __future__ import annotations

import argparse
import sys

from src.cli.common import add_common_job_arguments, create_context_from_args
from src.services.diarization import run_diarization
from src.utils.errors import PipelineError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run diarization feature")
    add_common_job_arguments(parser, source_label="오디오")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    context = create_context_from_args(args)

    try:
        result = run_diarization(context)
    except PipelineError as error:
        print(str(error), file=sys.stderr)
        return 1

    print(f"job_id={context.job_id}")
    print(f"audio={result.preprocessed_audio_path}")
    print(f"diarization={result.diarization_json_path}")
    print(f"rttm={result.diarization_rttm_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

