from __future__ import annotations

import argparse
import inspect
from pathlib import Path
import sys

from src.adapters.common import env_optional_int, load_runtime_env, project_root_from, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run pyannote diarization and write diarization.json")
    parser.add_argument("--audio", required=True, help="audio path")
    parser.add_argument("--output", required=True, help="diarization.json path")
    parser.add_argument("--output-dir", default=None, help="directory for diarization.rttm")
    parser.add_argument("--model", default=None, help="override pyannote model id/path")
    parser.add_argument("--num-speakers", type=int, default=None, help="fixed speaker count")
    parser.add_argument("--min-speakers", type=int, default=None, help="minimum speaker count")
    parser.add_argument("--max-speakers", type=int, default=None, help="maximum speaker count")
    return parser.parse_args()


def annotation_to_turns(annotation) -> list[dict]:
    turns = []
    if hasattr(annotation, "itertracks"):
        iterator = annotation.itertracks(yield_label=True)
        for segment, _, label in iterator:
            turns.append(
                {
                    "speaker_label": str(label),
                    "start_sec": round(float(segment.start), 3),
                    "end_sec": round(float(segment.end), 3),
                }
            )
    else:
        for item in annotation:
            if len(item) == 3:
                segment, _, label = item
            elif len(item) == 2:
                segment, label = item
            else:
                raise ValueError("Unsupported diarization annotation item.")
            turns.append(
                {
                    "speaker_label": str(label),
                    "start_sec": round(float(segment.start), 3),
                    "end_sec": round(float(segment.end), 3),
                }
            )
    turns.sort(key=lambda item: (item["start_sec"], item["end_sec"], item["speaker_label"]))
    return turns


def build_rttm_lines(turns: list[dict], uri: str = "meeting") -> str:
    lines = []
    for turn in turns:
        duration = max(0.0, turn["end_sec"] - turn["start_sec"])
        lines.append(
            f"SPEAKER {uri} 1 {turn['start_sec']:.3f} {duration:.3f} <NA> <NA> {turn['speaker_label']} <NA> <NA>"
        )
    return "\n".join(lines) + ("\n" if lines else "")


def build_pipeline_load_kwargs(from_pretrained, token: str | None) -> dict:
    if not token:
        return {}

    parameters = inspect.signature(from_pretrained).parameters
    if "token" in parameters:
        return {"token": token}
    if "use_auth_token" in parameters:
        return {"use_auth_token": token}
    return {}


def load_audio_for_pyannote(audio_path: Path):
    import torchaudio

    waveform, sample_rate = torchaudio.load(str(audio_path))
    if waveform.ndim == 1:
        waveform = waveform.unsqueeze(0)
    if waveform.shape[0] > 1:
        waveform = waveform.mean(dim=0, keepdim=True)
    return {
        "waveform": waveform,
        "sample_rate": int(sample_rate),
        "uri": audio_path.stem,
    }


def validate_pyannote_runtime(pyannote_version: str, model_name: str) -> None:
    major = int(str(pyannote_version).split(".", 1)[0])
    uses_community_1 = "speaker-diarization-community-1" in model_name
    if uses_community_1 and major < 4:
        raise RuntimeError(
            "pyannote/speaker-diarization-community-1 requires pyannote.audio 4.x. "
            f"Current version: {pyannote_version}. Upgrade pyannote.audio or switch to "
            "pyannote/speaker-diarization-3.1 for legacy 3.x runtime."
        )


def main() -> int:
    args = parse_args()
    project_root = project_root_from(Path(__file__))
    env = load_runtime_env(project_root)

    try:
        import pyannote.audio
        import torch
        from pyannote.audio import Pipeline
    except ImportError as error:
        print(f"pyannote dependencies are missing: {error}", file=sys.stderr)
        return 1

    model_name = args.model or env.get("DIARIZATION_MODEL", "pyannote/speaker-diarization-community-1")
    validate_pyannote_runtime(pyannote.audio.__version__, model_name)
    token = env.get("HUGGINGFACE_HUB_TOKEN", "").strip() or None
    pipeline = Pipeline.from_pretrained(
        model_name,
        **build_pipeline_load_kwargs(Pipeline.from_pretrained, token),
    )

    diarization_device = env.get("DIARIZATION_DEVICE", env.get("DEVICE", "")).strip()
    if diarization_device:
        if diarization_device.startswith("cuda") and not torch.cuda.is_available():
            raise RuntimeError("CUDA device was requested for diarization but is not available.")
        pipeline.to(torch.device(diarization_device))

    inference_kwargs = {}
    num_speakers = args.num_speakers if args.num_speakers is not None else env_optional_int(env, "DIARIZATION_NUM_SPEAKERS")
    min_speakers = args.min_speakers if args.min_speakers is not None else env_optional_int(env, "DIARIZATION_MIN_SPEAKERS")
    max_speakers = args.max_speakers if args.max_speakers is not None else env_optional_int(env, "DIARIZATION_MAX_SPEAKERS")
    if num_speakers is not None:
        inference_kwargs["num_speakers"] = num_speakers
    else:
        if min_speakers is not None:
            inference_kwargs["min_speakers"] = min_speakers
        if max_speakers is not None:
            inference_kwargs["max_speakers"] = max_speakers

    diarization_input = load_audio_for_pyannote(Path(args.audio).resolve())
    diarization_output = pipeline(diarization_input, **inference_kwargs)
    annotation = (
        getattr(diarization_output, "exclusive_speaker_diarization", None)
        or getattr(diarization_output, "speaker_diarization", None)
        or diarization_output
    )
    turns = annotation_to_turns(annotation)

    output_path = Path(args.output).resolve()
    write_json(
        output_path,
        {
            "provider": "pyannote.audio",
            "model": model_name,
            "speakers": turns,
        },
    )

    output_dir = Path(args.output_dir).resolve() if args.output_dir else output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    rttm_path = output_dir / "diarization.rttm"
    if hasattr(annotation, "write_rttm"):
        with rttm_path.open("w", encoding="utf-8") as file_pointer:
            annotation.write_rttm(file_pointer)
    else:
        rttm_path.write_text(build_rttm_lines(turns), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
