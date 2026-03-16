from __future__ import annotations

import argparse
from pathlib import Path
import sys

from src.adapters.common import (
    chunked,
    load_kwargs_from_env,
    load_runtime_env,
    move_model_to_device,
    normalize_language_name,
    project_root_from,
    read_json,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Qwen3-ForcedAligner and write align.json")
    parser.add_argument("--audio", required=True, help="16k mono wav path")
    parser.add_argument("--input-json", required=True, help="asr.json path")
    parser.add_argument("--output", required=True, help="align.json path")
    parser.add_argument("--model", default=None, help="override align model id/path")
    parser.add_argument("--language", default=None, help="force single language, e.g. Korean")
    return parser.parse_args()


def build_align_payload(*, model_name: str, aligned_segments: list[dict]) -> dict:
    return {
        "provider": "qwen_forced_aligner",
        "model": model_name,
        "segments": aligned_segments,
    }


def main() -> int:
    args = parse_args()
    project_root = project_root_from(Path(__file__))
    env = load_runtime_env(project_root)

    try:
        import torch
        from qwen_asr import Qwen3ForcedAligner
        from qwen_asr.inference.utils import SAMPLE_RATE, normalize_audio_input
    except ImportError as error:
        print(f"Qwen align dependencies are missing: {error}", file=sys.stderr)
        return 1

    model_name = args.model or env.get("ALIGN_MODEL", "Qwen/Qwen3-ForcedAligner-0.6B")
    forced_language = normalize_language_name(args.language or env.get("ALIGN_LANGUAGE"))
    max_batch_size = int(env.get("ALIGN_MAX_BATCH_SIZE", "8"))

    load_kwargs = load_kwargs_from_env(torch, env, "ALIGN")
    aligner = Qwen3ForcedAligner.from_pretrained(model_name, **load_kwargs)

    align_device = env.get("ALIGN_DEVICE", env.get("DEVICE", "")).strip()
    if "device_map" not in load_kwargs:
        move_model_to_device(aligner.model, torch, align_device)

    asr_payload = read_json(Path(args.input_json).resolve())
    audio_waveform = normalize_audio_input(str(Path(args.audio).resolve()))
    audio_sample_count = len(audio_waveform)
    asr_segments = [segment for segment in asr_payload.get("segments", []) if str(segment.get("text", "")).strip()]

    if not asr_segments:
        write_json(Path(args.output).resolve(), build_align_payload(model_name=model_name, aligned_segments=[]))
        return 0

    tasks = []
    for segment in asr_segments:
        start_sec = float(segment.get("start_sec", 0.0))
        end_sec = float(segment.get("end_sec", start_sec))
        start_index = max(0, min(audio_sample_count, int(round(start_sec * SAMPLE_RATE))))
        end_index = max(start_index + 1, min(audio_sample_count, int(round(end_sec * SAMPLE_RATE))))
        chunk_waveform = audio_waveform[start_index:end_index]
        language = normalize_language_name(segment.get("language") or forced_language or asr_payload.get("language"))
        if not language:
            raise ValueError(
                "Alignment requires a single language. Set ALIGN_LANGUAGE or ASR_FORCE_LANGUAGE in .env."
            )
        tasks.append(
            {
                "audio": (chunk_waveform, SAMPLE_RATE),
                "text": str(segment["text"]).strip(),
                "language": language,
                "offset_sec": start_sec,
                "fallback_end_sec": end_sec,
            }
        )

    aligned_segments: list[dict] = []
    for batch in chunked(tasks, max_batch_size):
        batch_results = aligner.align(
            audio=[item["audio"] for item in batch],
            text=[item["text"] for item in batch],
            language=[item["language"] for item in batch],
        )
        for task, result in zip(batch, batch_results):
            words = [
                {
                    "text": item.text,
                    "start_sec": round(float(item.start_time) + task["offset_sec"], 3),
                    "end_sec": round(float(item.end_time) + task["offset_sec"], 3),
                }
                for item in result.items
            ]
            start_sec = words[0]["start_sec"] if words else round(task["offset_sec"], 3)
            end_sec = words[-1]["end_sec"] if words else round(task["fallback_end_sec"], 3)
            aligned_segments.append(
                {
                    "text": task["text"],
                    "start_sec": start_sec,
                    "end_sec": end_sec,
                    "words": words,
                }
            )

    payload = build_align_payload(model_name=model_name, aligned_segments=aligned_segments)
    write_json(Path(args.output).resolve(), payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
