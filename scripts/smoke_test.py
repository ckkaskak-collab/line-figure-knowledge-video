#!/usr/bin/env python3
"""Exercise a fresh installation and local handoff using synthetic, clearly labeled timing data."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from common import ROOT, read_json, write_json


def run_demo(output):
    output.mkdir(parents=True, exist_ok=False)
    installed = output / "clean skills" / "line-figure-knowledge-video"
    def run(script, *args, root=ROOT):
        result = subprocess.run([sys.executable, str(root / "scripts" / script), *map(str, args)], cwd=output, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(f"{script}: {result.stderr or result.stdout}")
        return result.stdout.strip()
    run("install.py", "--destination", installed)
    run("doctor.py", root=installed)
    examples = installed / "examples/quickstart"
    project = output / "new video"
    run("init_project.py", "--script", examples / "script.txt", "--output", project, root=installed)
    run("align_audio.py", "--script", project / "script.txt", "--asr", examples / "acoustic-fixture.json", "--phrases", examples / "phrases.txt", "--output", project / "alignment", root=installed)
    result = read_json(project / "alignment/phrase-acoustic.json")
    assert result["shared_boundaries_ms"] == [0, 1150, 2500]
    assert result["shared_boundaries_frames"] == [0, 35, 75]
    cards = {"fps": "30", "cards": [{"text": "先查资料，再回答。", "start_frame": 6, "end_frame": 66}]}
    write_json(project / "final-cards.json", cards)
    run("captions_to_srt.py", "--input", project / "final-cards.json", "--output", project / "delivery/final.srt", root=installed)
    assert "先查资料，再回答。" in (project / "delivery/final.srt").read_text(encoding="utf-8")
    run("template_payload.py", "--template", "compare", "--duration-frames", 150, "--beats", "0,45,100", "--props", examples / "compare-props.json", "--output", project / "assets/broll/compare.json", root=installed)
    payload = read_json(project / "assets/broll/compare.json")
    assert next(p for p in payload["properties"] if p["key"] == "staticPreview")["defaultValue"] is False
    preview = json.loads(run("synthesize_doubao.py", "--script", project / "script.txt", "--speaker", "offline-preview", "--output", project / "audio/preview", root=installed))
    assert preview["mode"] == "preview" and preview["speech_rate"] == 15
    assert not (project / "audio/preview").exists()
    report = {"status": "pass", "checks": ["fresh installation in path with spaces", "package references", "project initialization", "silence-preserving acoustic and continuous handoff", "frame boundary rounding", "caption punctuation", "editable template payload", "TTS preview without credentials or network"], "fixture": "synthetic timing only", "external_generation": False, "finished_video": False}
    write_json(output / "smoke-report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New directory for retained demo files; otherwise use a temporary directory")
    args = parser.parse_args()
    try:
        if args.output:
            result = run_demo(args.output.resolve())
        else:
            with tempfile.TemporaryDirectory(prefix="line-figure-check-") as temp:
                result = run_demo(Path(temp) / "demo")
    except (OSError, ValueError, RuntimeError, AssertionError) as error:
        parser.exit(1, f"Smoke test failed: {error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
