#!/usr/bin/env python3
"""Align approved phrases to actual word timestamps; never interpolate missing words."""
import argparse
import difflib
import json
from pathlib import Path

from common import final_frame, fps_value, frame_at, normalized, read_json, render_srt, sha256, write_json


def align(script, asr, phrases, fps="30"):
    fps = str(fps_value(fps))
    duration = asr["duration_ms"]
    if type(duration) is not int or duration <= 0:
        raise ValueError("duration_ms must be a positive measured integer")
    target = normalized(script)
    phrases = [p.strip() for p in phrases if p.strip()]
    if not target or any(not normalized(p) for p in phrases):
        raise ValueError("Script and phrases must contain spoken text")
    if normalized("".join(phrases)) != target:
        raise ValueError("Phrases must cover the approved script, in order, without word changes")
    words = []
    last_end = 0
    for word in asr["words"]:
        text = normalized(word.get("reviewed_text", word["text"]))
        if not text:
            continue
        start, end = word["start_ms"], word["end_ms"]
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= duration:
            raise ValueError("Invalid ASR word timestamp")
        if start < last_end:
            raise ValueError("ASR words overlap; review the original timestamps before alignment")
        words.append({"text": text, "start_ms": start, "end_ms": end})
        last_end = end
    recognized = "".join(w["text"] for w in words)
    if recognized != target:
        differences = [dict(kind=op, script=target[a:b], asr=recognized[c:d]) for op, a, b, c, d in difflib.SequenceMatcher(None, target, recognized, autojunk=False).get_opcodes() if op != "equal"]
        raise ValueError("ASR text needs review: " + json.dumps(differences, ensure_ascii=False))
    starts, ends, offset = {}, {}, 0
    for word in words:
        starts[offset] = word["start_ms"]
        offset += len(word["text"])
        ends[offset] = word["end_ms"]
    rows, offset = [], 0
    for i, phrase in enumerate(phrases, 1):
        end_offset = offset + len(normalized(phrase))
        if offset not in starts or end_offset not in ends:
            raise ValueError(f"Phrase {i} splits an ASR word; merge phrases or obtain finer real timestamps")
        rows.append({"id": f"P{i:03}", "text": phrase, "start_ms": starts[offset], "end_ms": ends[end_offset]})
        offset = end_offset
    boundaries = [0] + [(a["end_ms"] + b["start_ms"]) // 2 for a, b in zip(rows, rows[1:])] + [duration]
    frames = [frame_at(ms, fps) for ms in boundaries[:-1]] + [final_frame(duration, fps)]
    if any(b <= a for a, b in zip(boundaries, boundaries[1:])) or any(b <= a for a, b in zip(frames, frames[1:])):
        raise ValueError("Phrase boundaries collapse in time or frames; review the phrase split")
    for i, row in enumerate(rows):
        row.update(continuous_start_ms=boundaries[i], continuous_end_ms=boundaries[i+1], from_frame=frames[i], end_frame=frames[i+1])
    return {"duration_ms": duration, "fps": fps, "source": asr.get("source", "provided word timestamps"), "frame_rule": "shared half-up; final ceil", "phrases": rows, "shared_boundaries_ms": boundaries, "shared_boundaries_frames": frames}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--asr", required=True, type=Path)
    parser.add_argument("--phrases", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--fps", default="30")
    args = parser.parse_args()
    if args.output.exists():
        parser.exit(1, "Output already exists; preserve it and choose a new directory.\n")
    try:
        result = align(args.script.read_text(encoding="utf-8"), read_json(args.asr), args.phrases.read_text(encoding="utf-8").splitlines(), args.fps)
    except (OSError, ValueError, KeyError, TypeError) as error:
        args.output.mkdir(parents=True, exist_ok=False)
        write_json(args.output / "alignment-review.json", {"status": "needs_review", "reason": str(error)})
        parser.exit(1, f"Alignment stopped for review: {error}\n")
    args.output.mkdir(parents=True)
    result["inputs"] = {"script_sha256": sha256(args.script), "asr_sha256": sha256(args.asr), "phrases_sha256": sha256(args.phrases)}
    write_json(args.output / "phrase-acoustic.json", result)
    (args.output / "vo-align.txt").write_text("\n".join(f"[{p['continuous_start_ms']}ms-{p['continuous_end_ms']}ms] {p['text']}" for p in result["phrases"]) + "\n", encoding="utf-8")
    (args.output / "captions.srt").write_text(render_srt(result["phrases"]), encoding="utf-8")
    print(json.dumps({"duration_ms": result["duration_ms"], "phrases": len(result["phrases"]), "last_end_ms": result["shared_boundaries_ms"][-1], "frames": result["shared_boundaries_frames"][-1]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
