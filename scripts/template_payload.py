#!/usr/bin/env python3
"""Instantiate a bundled B-roll template using explicitly supplied local-frame anchors."""
import argparse
import copy
from pathlib import Path
import re

from common import ROOT, read_json, write_json


def instantiate(template_id, duration, beats, overrides=None):
    index = read_json(ROOT / "assets/broll/templates/index.json")
    entry = next((e for e in index["templates"] if e["id"] == template_id), None)
    if entry is None:
        raise ValueError("Unknown template; see assets/broll/templates/index.json")
    template = read_json(ROOT / "assets/broll/templates" / entry["file"])
    if type(duration) is not int or duration <= 0 or len(beats) != len(template["timing_keys"]):
        raise ValueError("Supply a positive frame duration and exactly three action frames")
    if any(type(b) is not int or b < 0 for b in beats) or any(b <= a for a, b in zip(beats, beats[1:])):
        raise ValueError("Action frames must be nonnegative, strictly increasing integers")
    properties = copy.deepcopy(template["properties"])
    known = {p["key"] for p in properties}
    overrides = dict(overrides or {})
    unknown = set(overrides) - known
    if unknown:
        raise ValueError("Unknown properties: " + ", ".join(sorted(unknown)))
    if set(overrides).intersection(template["timing_keys"]):
        raise ValueError("Use --beats for timing, not property overrides")
    overrides.update(dict(zip(template["timing_keys"], beats)))
    overrides.update({k: v for k, v in {"staticPreview": False, "previewStage": "auto"}.items() if k in known})
    for prop in properties:
        key = prop["key"]
        if key in template["timing_keys"]:
            prop["max"] = duration - 1
        if key in overrides:
            prop["defaultValue"] = overrides[key]
        value = prop["defaultValue"]
        kind = prop["type"]
        if kind == "number":
            if type(value) not in (int, float) or not prop.get("min", float("-inf")) <= value <= prop.get("max", float("inf")):
                raise ValueError(f"Invalid numeric property: {key}")
        elif kind == "boolean" and type(value) is not bool:
            raise ValueError(f"Expected boolean: {key}")
        elif kind in ("text", "font", "color", "select") and not isinstance(value, str):
            raise ValueError(f"Expected string: {key}")
        if kind == "color" and not re.fullmatch(r"#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?", value):
            raise ValueError(f"Expected hex color: {key}")
        if kind == "select" and value not in [o["value"] for o in prop["options"]]:
            raise ValueError(f"Unknown select value: {key}")
    values = {p["key"]: p["defaultValue"] for p in properties}
    tail = max(values.get("linkFrames", 0), values.get("revealFrames", 0), template["minimum_tail_frames"])
    if beats[-1] + tail >= duration:
        raise ValueError("Last action cannot finish within this clip; extend duration or move anchors")
    return {"name": "line-figure_" + template_id, "code": template["code"], "width": template["width"], "height": template["height"], "durationInFrames": duration, "properties": properties, "description": template["semantic"] + ("；真实截图单独放在上层，不能用示意替代。" if entry["external_media_required"] else "")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True)
    parser.add_argument("--duration-frames", type=int, required=True)
    parser.add_argument("--beats", required=True, help="Comma-separated real action frame anchors")
    parser.add_argument("--props", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        payload = instantiate(args.template, args.duration_frames, [int(v) for v in args.beats.split(",")], read_json(args.props) if args.props else {})
        write_json(args.output, payload)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Template preparation failed: {error}\n")
    print(f"MG payload prepared (not uploaded): {args.output}")


if __name__ == "__main__":
    main()
