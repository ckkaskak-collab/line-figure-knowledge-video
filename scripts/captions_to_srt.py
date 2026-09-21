#!/usr/bin/env python3
"""Convert normalized final caption Cards to SRT, preserving display text and frame timing."""
import argparse
from fractions import Fraction
from pathlib import Path

from common import fps_value, read_json, render_srt, round_half_up


def convert(data):
    fps = fps_value(data["fps"])
    rows = []
    for card in data["cards"]:
        start, end = card["start_frame"], card["end_frame"]
        if type(start) is not int or type(end) is not int or start < 0 or end <= start:
            raise ValueError("Caption frames must be nonnegative integers with start < end")
        rows.append({"text": card["text"], "start_ms": round_half_up(Fraction(start * 1000) / fps), "end_ms": round_half_up(Fraction(end * 1000) / fps)})
    return render_srt(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        text = convert(read_json(args.input))
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(text)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Caption conversion failed: {error}\n")
    print(f"SRT written: {args.output}")


if __name__ == "__main__":
    main()
