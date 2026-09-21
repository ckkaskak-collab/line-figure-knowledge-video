#!/usr/bin/env python3
"""Preserve faster-whisper large-v3 output and expose real word timestamps for review."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time
import warnings

from common import round_half_up, sha256, write_json
from fractions import Fraction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model", default="large-v3")
    parser.add_argument("--language", default="zh")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--offline", action="store_true", help="Only use models already cached")
    parser.add_argument("--initial-prompt", default="简体中文。")
    args = parser.parse_args()
    partial = args.output.with_suffix(".partial.json")
    if args.output.exists() or partial.exists():
        parser.exit(1, "Prior transcript or partial output exists; inspect it and choose a new path.\n")
    if not args.audio.is_file():
        parser.exit(1, "Audio file does not exist.\n")
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        parser.exit(1, "Install the optional ASR environment: python -m pip install -r requirements-asr.txt\n")
    started = time.monotonic()
    raw, words = [], []
    try:
        # Numerical failures must not silently become timing evidence.
        warnings.filterwarnings("error", category=RuntimeWarning, module=r"faster_whisper(\.|$)")
        print(f"Loading {args.model} ({args.device}, {args.compute_type}); offline={args.offline}", flush=True)
        model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type, local_files_only=args.offline)
        segments, info = model.transcribe(str(args.audio), language=args.language, word_timestamps=True, beam_size=5, vad_filter=True, initial_prompt=args.initial_prompt)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        for segment in segments:
            row = asdict(segment)
            raw.append(row)
            for word in segment.words or []:
                words.append({"text": word.word, "start_ms": round_half_up(Fraction(str(word.start)) * 1000), "end_ms": round_half_up(Fraction(str(word.end)) * 1000)})
            partial.write_text(json.dumps({"status": "in_progress", "segments": raw}, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"{segment.start:.2f}-{segment.end:.2f} {segment.text}", flush=True)
        if not words:
            raise ValueError("No speech words recognized; inspect the audio and language")
        result = {"source": "faster-whisper", "model": args.model, "device": args.device, "compute_type": args.compute_type, "audio_sha256": sha256(args.audio), "duration_ms": round_half_up(Fraction(str(info.duration)) * 1000), "language": info.language, "words": words, "segments": raw, "wall_seconds": round(time.monotonic() - started, 3), "review_status": "unreviewed"}
        write_json(args.output, result)
    except RuntimeWarning as error:
        parser.exit(1, f"Numerical ASR warning: {error}\nDo not use these timestamps. Check the Python/numerical-library environment or obtain an independent ASR result.\n")
    except Exception as error:
        parser.exit(1, f"Transcription failed ({type(error).__name__}): {error}\nPartial output, if present, is not a completed transcript.\n")
    print(f"Transcript saved for script/timing review: {args.output}")


if __name__ == "__main__":
    main()
