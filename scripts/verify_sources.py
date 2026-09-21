#!/usr/bin/env python3
"""Verify preserved prompt bytes against provenance and captured source text."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def fnv1a_utf16(text):
    raw = text.encode("utf-16-le")
    value = 0x811C9DC5
    for offset in range(0, len(raw), 2):
        unit = int.from_bytes(raw[offset:offset + 2], "little")
        value = ((value ^ unit) * 0x01000193) & 0xFFFFFFFF
    return f"{value:08x}"


def verify(root):
    manifest = json.loads((root / "references/source-manifest.json").read_bytes())
    sources = manifest["sources"]
    errors = []
    snapshots = {}
    for source_id, source in sources.items():
        path = root / source["snapshot_path"]
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != source["snapshot_sha256"]:
            errors.append(f"Source snapshot changed: {path}")
        snapshots[source_id] = json.loads(raw)

    x_records = {row["index"]: row for row in snapshots["x"]["prompts"]}
    doc = snapshots["feishu"]["data"]["document"]
    if (doc["document_id"] != sources["feishu"]["document_id"]
            or doc["revision_id"] != sources["feishu"]["revision_id"]):
        errors.append("Feishu snapshot document or revision does not match provenance")
    tree = ET.fromstring("<root>" + doc["content"].replace("<br/>", "\n") + "</root>")
    feishu_records = {
        pre.get("id"): "".join(pre.find("code").itertext())
        for pre in tree.iter("pre") if pre.find("code") is not None
    }
    prompts = manifest["prompts"]
    expected_ids = {f"x-{index:02d}" for index in range(1, 7)} | {
        "feishu-visual-v2", "feishu-chatcut-v2"
    }
    if len(prompts) != 8 or {row["id"] for row in prompts} != expected_ids:
        errors.append("Expected six X prompts and two Feishu prompts")
    for prompt in prompts:
        path = root / prompt["path"]
        raw = path.read_bytes()
        text = raw.decode("utf-8")
        actual = {
            "bytes_utf8": len(raw),
            "length_utf16": len(text.encode("utf-16-le")) // 2,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "fnv1a_utf16": fnv1a_utf16(text),
        }
        for field, value in actual.items():
            if value != prompt[field]:
                errors.append(f"{prompt['id']}: {field} mismatch")
        if prompt["source"] == "x":
            observed = x_records[prompt["source_index"]]
            for field in ("length_utf16", "fnv1a_utf16"):
                if actual[field] != observed[field]:
                    errors.append(f"{prompt['id']}: differs from captured X browser text")
        elif text != feishu_records[prompt["block_id"]]:
            errors.append(f"{prompt['id']}: differs from original Feishu code block")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        errors = verify(args.root)
    except (OSError, UnicodeError, KeyError, ValueError, ET.ParseError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    if errors:
        print("FAIL:\n" + "\n".join(errors), file=sys.stderr)
        return 1
    print("PASS: six X prompts match captured browser fingerprints; both Feishu prompts match revision 30 code blocks; all UTF-8 SHA-256 checks pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
