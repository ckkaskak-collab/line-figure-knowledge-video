#!/usr/bin/env python3
"""Check the downloaded package without credentials, network requests, or external generation."""
import argparse
import ast
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import unquote

from common import ROOT, read_json
from verify_sources import verify
from template_payload import instantiate


def check_package():
    errors = []
    if sys.version_info < (3, 9):
        errors.append("Python 3.9 or later is required")
    for name in ("SKILL.md", "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "assets/character/reference.jpg", "assets/broll/approved-light-gray-handdrawn.png"):
        if not (ROOT / name).is_file():
            errors.append("Missing packaged file: " + name)
    try:
        errors.extend(verify(ROOT))
    except (OSError, ValueError, KeyError) as error:
        errors.append("Original source verification failed: " + str(error))
    for path in ROOT.rglob("*.py"):
        if any(part in {".venv", "venv", ".git"} for part in path.relative_to(ROOT).parts):
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeError) as error:
            errors.append(f"Invalid Python file {path.relative_to(ROOT)}: {error}")
    for path in ROOT.rglob("*.md"):
        if any(part in {".venv", "venv", ".git"} for part in path.relative_to(ROOT).parts):
            continue
        for link in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            link = unquote(link.strip("<> ").split("#")[0])
            if not link or "://" in link or link.startswith("mailto:"):
                continue
            target = (path.parent / link).resolve()
            if not target.is_relative_to(ROOT):
                errors.append(f"External local dependency in {path.relative_to(ROOT)}: {link}")
            elif not target.exists():
                errors.append(f"Broken link in {path.relative_to(ROOT)}: {link}")
    try:
        index = read_json(ROOT / "assets/broll/templates/index.json")
        for template in index["templates"]:
            instantiate(template["id"], 300, [0, 60, 180])
    except (OSError, ValueError, KeyError) as error:
        errors.append("Template validation failed: " + str(error))
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    errors = check_package()
    optional = {name: importlib.util.find_spec(name) is not None for name in ("httpx", "faster_whisper")}
    optional.update({name: bool(shutil.which(name)) for name in ("ffmpeg", "ffprobe")})
    result = {"package": "fail" if errors else "pass", "errors": errors, "optional_local_tools": optional, "external_tools": "Image generation and ChatCut must be checked in your assistant; no account or paid service was called."}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("PACKAGE " + result["package"].upper())
        for error in errors:
            print("- " + error)
        for name, present in optional.items():
            print(f"Optional {name}: {'available' if present else 'not installed'}")
        print(result["external_tools"])
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
