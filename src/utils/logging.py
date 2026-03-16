from __future__ import annotations

from logging import FileHandler, Formatter, Logger, StreamHandler, getLogger
from pathlib import Path


def setup_job_logger(job_id: str, log_path: Path) -> Logger:
    logger = getLogger(f"asr_pipeline.{job_id}")
    logger.setLevel("INFO")
    logger.handlers.clear()
    logger.propagate = False

    formatter = Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler = FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger
