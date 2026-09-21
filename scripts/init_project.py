#!/usr/bin/env python3
"""Create a new, portable project from an approved script and optional existing audio."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import shutil
import subprocess
import wave

from common import ROOT, fps_value, round_half_up, sha256, write_json


def audio_duration(path):
    try:
        with wave.open(str(path), "rb") as audio:
            return round_half_up(Fraction(audio.getnframes() * 1000, audio.getframerate()))
    except (wave.Error, EOFError):
        if not shutil.which("ffprobe"):
            return None
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)], capture_output=True, text=True)
        if result.returncode:
            raise ValueError("ffprobe could not decode the input audio")
        return round_half_up(Fraction(json.loads(result.stdout)["format"]["duration"]) * 1000)


def initialize(script, output, audio=None, character=None, fps="30"):
    script, output = Path(script), Path(output)
    fps = str(fps_value(fps))
    if not script.read_text(encoding="utf-8").strip():
        raise ValueError("Script is empty")
    character = Path(character) if character else ROOT / "assets/character/reference.jpg"
    if not character.is_file():
        raise ValueError("Character reference is missing")
    duration = audio_duration(audio) if audio else None
    if audio and (duration is not None and duration <= 0):
        raise ValueError("Audio has no duration")
    output.mkdir(parents=True, exist_ok=False)
    for name in ("audio", "assets/aroll", "assets/broll", "assets/evidence", "qa", "delivery"):
        (output / name).mkdir(parents=True, exist_ok=True)
    shutil.copy2(script, output / "script.txt")
    char_name = "assets/character-reference" + character.suffix.lower()
    shutil.copy2(character, output / char_name)
    voice = {"status": "missing", "path": None, "duration_ms": None}
    if audio:
        voice_name = "audio/source" + Path(audio).suffix.lower()
        shutil.copy2(audio, output / voice_name)
        voice = {"status": "provided", "path": voice_name, "sha256": sha256(output / voice_name), "duration_ms": duration}
    state = {
        "schema_version": 1, "stage": "inputs_ready" if audio else "awaiting_audio",
        "script": {"path": "script.txt", "sha256": sha256(output / "script.txt")},
        "voice": voice,
        "visual": {"character": char_name, "character_sha256": sha256(output / char_name), "aroll": "key-state-images", "broll": "light-gray-handdrawn"},
        "format": {"width": 1920, "height": 1080, "fps": fps},
        "records": {}, "shots": [], "chatcut": {},
        "verification": {"alignment": False, "timeline": False, "composed_frames": False, "continuous_viewing": False, "continuous_listening": False, "export": False},
        "delivery": {}, "known_limits": [],
        "next_action": "transcribe_and_review_audio" if audio else "provide_audio_or_configure_authorized_tts"
    }
    write_json(output / "project-state.json", state)
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--audio", type=Path)
    parser.add_argument("--character", type=Path)
    parser.add_argument("--fps", default="30")
    args = parser.parse_args()
    try:
        state = initialize(args.script, args.output, args.audio, args.character, args.fps)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Project initialization failed: {error}\n")
    print(json.dumps({"project": str(args.output), "stage": state["stage"], "duration_ms": state["voice"]["duration_ms"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
