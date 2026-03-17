from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

from src.adapters.common import (
    chunked,
    load_kwargs_from_env,
    load_runtime_env,
    move_model_to_device,
    normalize_language_name,
    project_root_from,
    unique_csv,
    write_json,
)


@dataclass(slots=True)
class LoadedAsrRuntime:
    model_name: str
    forced_language: str
    context: str
    chunk_max_seconds: float
    max_batch_size: int
    model: object
    sample_rate: int
    normalize_audio_input: object
    split_audio_into_chunks: object


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Qwen3-ASR and write asr.json")
    parser.add_argument("--audio", required=True, help="16k mono wav path")
    parser.add_argument("--output", required=True, help="output JSON path")
    parser.add_argument("--model", default=None, help="override ASR model id/path")
    parser.add_argument("--language", default=None, help="force language, e.g. Korean")
    parser.add_argument("--context", default=None, help="optional transcription context")
    return parser.parse_args()


def build_asr_payload(
    *,
    model_name: str,
    chunk_results: list[dict],
) -> dict:
    segments = []
    for result in chunk_results:
        text = result["text"].strip()
        if not text:
            continue
        segments.append(
            {
                "text": text,
                "start_sec": round(result["start_sec"], 3),
                "end_sec": round(result["end_sec"], 3),
                "words": [],
                "language": result["language"],
            }
        )
    return {
        "provider": "qwen_asr",
        "model": model_name,
        "language": unique_csv([item["language"] for item in chunk_results]),
        "segments": segments,
    }


def load_asr_runtime(
    env: dict[str, str],
    *,
    model_name: str | None = None,
    language: str | None = None,
    context: str | None = None,
) -> LoadedAsrRuntime:
    try:
        import torch
        from qwen_asr import Qwen3ASRModel
        from qwen_asr.inference.utils import SAMPLE_RATE, normalize_audio_input, split_audio_into_chunks
    except ImportError as error:
        raise RuntimeError(f"Qwen ASR dependencies are missing: {error}") from error

    resolved_model_name = model_name or env.get("ASR_MODEL", "Qwen/Qwen3-ASR-1.7B")
    forced_language = normalize_language_name(language or env.get("ASR_FORCE_LANGUAGE"))
    runtime_context = (context or env.get("ASR_CONTEXT", "")).strip()
    chunk_max_seconds = float(env.get("ASR_CHUNK_MAX_SECONDS", env.get("ALIGN_CHUNK_MAX_SECONDS", "180")))
    max_batch_size = int(env.get("ASR_MAX_INFERENCE_BATCH_SIZE", "4"))
    max_new_tokens = int(env.get("ASR_MAX_NEW_TOKENS", "512"))

    load_kwargs = load_kwargs_from_env(torch, env, "ASR")
    asr_model = Qwen3ASRModel.from_pretrained(
        resolved_model_name,
        max_inference_batch_size=max_batch_size,
        max_new_tokens=max_new_tokens,
        **load_kwargs,
    )

    asr_device = env.get("ASR_DEVICE", env.get("DEVICE", "")).strip()
    if "device_map" not in load_kwargs:
        move_model_to_device(asr_model.model, torch, asr_device)

    return LoadedAsrRuntime(
        model_name=resolved_model_name,
        forced_language=forced_language,
        context=runtime_context,
        chunk_max_seconds=chunk_max_seconds,
        max_batch_size=max_batch_size,
        model=asr_model,
        sample_rate=SAMPLE_RATE,
        normalize_audio_input=normalize_audio_input,
        split_audio_into_chunks=split_audio_into_chunks,
    )


def transcribe_with_runtime(
    runtime: LoadedAsrRuntime,
    *,
    audio_path: Path,
    language: str | None = None,
    context: str | None = None,
) -> dict:
    forced_language = normalize_language_name(language) or runtime.forced_language
    runtime_context = (context if context is not None else runtime.context).strip()

    waveform = runtime.normalize_audio_input(str(audio_path.resolve()))
    total_duration = round(len(waveform) / runtime.sample_rate, 3)
    chunks = runtime.split_audio_into_chunks(
        wav=waveform,
        sr=runtime.sample_rate,
        max_chunk_sec=runtime.chunk_max_seconds,
    )

    offsets = [offset_sec for _, offset_sec in chunks]
    bounds = offsets[1:] + [total_duration]
    chunk_inputs = [(chunk_wav, runtime.sample_rate) for chunk_wav, _ in chunks]
    languages = [forced_language] * len(chunk_inputs) if forced_language else None

    raw_chunk_results = []
    for batch_indexes in chunked(list(range(len(chunk_inputs))), runtime.max_batch_size):
        batch_audio = [chunk_inputs[index] for index in batch_indexes]
        batch_context = [runtime_context for _ in batch_indexes]
        batch_languages = [languages[index] for index in batch_indexes] if languages else None
        outputs = runtime.model.transcribe(
            audio=batch_audio,
            context=batch_context,
            language=batch_languages,
            return_time_stamps=False,
        )
        for local_index, output in zip(batch_indexes, outputs):
            raw_chunk_results.append(
                {
                    "text": output.text,
                    "language": normalize_language_name(output.language or forced_language),
                    "start_sec": offsets[local_index],
                    "end_sec": bounds[local_index],
                }
            )

    return build_asr_payload(model_name=runtime.model_name, chunk_results=raw_chunk_results)


def main() -> int:
    args = parse_args()
    project_root = project_root_from(Path(__file__))
    env = load_runtime_env(project_root)

    try:
        runtime = load_asr_runtime(
            env,
            model_name=args.model,
            language=args.language,
            context=args.context,
        )
        payload = transcribe_with_runtime(runtime, audio_path=Path(args.audio).resolve())
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1
    write_json(Path(args.output).resolve(), payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
