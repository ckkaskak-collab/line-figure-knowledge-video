#!/usr/bin/env python3
"""Install this entire Skill locally. Existing versions require --replace and are backed up."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import sys
import tempfile

from common import ROOT

EXCLUDED = {".git", ".DS_Store", "__pycache__", ".venv", "venv", "outputs", "projects", ".skill-backups"}


def install(destination, replace=False):
    destination = Path(destination).expanduser().absolute()
    resolved = destination.resolve()
    if destination.is_symlink():
        raise ValueError("Destination must not be a symlink")
    if ROOT == resolved or ROOT in resolved.parents or resolved in ROOT.parents:
        raise ValueError("Destination must be separate from the source package")
    if destination.exists() and not replace:
        raise ValueError("Destination exists; use --replace to back it up before upgrading")
    if destination.exists() and not (destination / "SKILL.md").is_file():
        raise ValueError("Existing destination is not a Skill; refusing to replace it")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".line-figure-install-", dir=destination.parent))
    backup = None
    try:
        shutil.copytree(ROOT, staging / "package", ignore=shutil.ignore_patterns(*EXCLUDED, "*.pyc", ".env*", "doubao-tts.json"))
        if destination.exists():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            backup = destination.parent / ".skill-backups" / f"{destination.name}-{stamp}"
            backup.parent.mkdir(exist_ok=True)
            destination.rename(backup)
        try:
            (staging / "package").rename(destination)
        except OSError:
            if backup is not None and not destination.exists():
                backup.rename(destination)
            raise
    finally:
        shutil.rmtree(staging)
    return destination, backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "skills" / "line-figure-knowledge-video"
    parser.add_argument("--destination", type=Path, default=default)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    try:
        destination, backup = install(args.destination, args.replace)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Install failed: {error}\n")
    print(f"Installed: {destination}")
    if backup:
        print(f"Previous version: {backup}")
    print("Open a new task and invoke $line-figure-knowledge-video.")


if __name__ == "__main__":
    main()
