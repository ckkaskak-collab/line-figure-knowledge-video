"""Small, dependency-free helpers shared by the workflow tools."""
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import unicodedata

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalized(text):
    """Ignore prose punctuation without erasing numbers, units or operators."""
    text = "".join(unicodedata.normalize("NFKC", text).split())
    result = []
    for i, char in enumerate(text):
        between_digits = 0 < i < len(text) - 1 and text[i - 1].isdigit() and text[i + 1].isdigit()
        if (char.isalnum() or unicodedata.category(char).startswith("S")
                or char in "-/%‰_#@&" or (char in ".,:" and between_digits)):
            result.append(char.lower())
    return "".join(result)


def fps_value(value):
    fps = Fraction(str(value))
    if not 0 < fps <= 240:
        raise ValueError("fps must be greater than 0 and no more than 240")
    return fps


def round_half_up(value):
    value = Fraction(value)
    if value < 0:
        raise ValueError("time must not be negative")
    return (2 * value.numerator + value.denominator) // (2 * value.denominator)


def frame_at(ms, fps):
    return round_half_up(Fraction(str(ms)) * fps_value(fps) / 1000)


def final_frame(ms, fps):
    value = Fraction(str(ms)) * fps_value(fps) / 1000
    return -(-value.numerator // value.denominator)


def srt_time(ms):
    if not isinstance(ms, int) or ms < 0:
        raise ValueError("SRT milliseconds must be nonnegative integers")
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def render_srt(rows):
    previous_end = 0
    blocks = []
    for number, row in enumerate(rows, 1):
        start, end, text = row["start_ms"], row["end_ms"], row["text"]
        if start < previous_end or end <= start or not str(text).strip():
            raise ValueError(f"Invalid or overlapping caption {number}")
        if "\n\n" in text or "\r" in text:
            raise ValueError(f"Caption {number} contains an SRT block separator")
        blocks.append(f"{number}\n{srt_time(start)} --> {srt_time(end)}\n{text}")
        previous_end = end
    if not blocks:
        raise ValueError("No captions supplied")
    return "\n\n".join(blocks) + "\n"
