#!/usr/bin/env python3
"""One complete-text Doubao V3 SSE request. Preview by default; never retry."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import stat
import time
import uuid
import wave

ENDPOINT = "https://openspeech.bytedance.com/api/v3/tts/unidirectional/sse"


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path, help="New audio output directory")
    parser.add_argument("--speaker", required=True)
    parser.add_argument("--speech-rate", default=15, type=int, help="Doubao V3 integer rate; default 15 = 1.15x")
    parser.add_argument("--config", type=Path, default=Path.home() / ".config/line-figure-knowledge-video/doubao-tts.json")
    parser.add_argument("--synthesize", action="store_true", help="Send the already-authorized request")
    args = parser.parse_args()
    if not -50 <= args.speech_rate <= 100:
        parser.error("speech-rate must be between -50 and 100")
    source = args.script.read_text(encoding="utf-8")
    if not source.strip():
        parser.error("script is empty")
    out = args.output
    journal = out / "tts-attempt.json"
    guarded = [journal, out / "tts-request.json", out / "tts-response.json", out / "vo-full.wav", out / "vo-source.pcm"]
    if any(path.exists() for path in guarded):
        parser.error("Prior attempt or audio exists. Inspect and reuse it; no automatic retry or overwrite.")
    body = {"user": {"uid": "line_figure_video"}, "req_params": {
        "text": source, "speaker": args.speaker,
        "audio_params": {"format": "pcm", "sample_rate": 44100,
                         "speech_rate": args.speech_rate, "loudness_rate": 0, "enable_subtitle": True}}}
    summary = {"mode": "synthesize" if args.synthesize else "preview",
               "text_sha256": hashlib.sha256(source.encode()).hexdigest(),
               "text_characters": len(source), "speaker": args.speaker,
               "speech_rate": args.speech_rate, "sample_rate": 44100,
               "resource_id": "seed-tts-2.0", "output": str(out)}
    if not args.synthesize:
        print(json.dumps(summary, ensure_ascii=False))
        return
    try:
        import httpx
    except ImportError:
        parser.error("Install optional TTS dependency: python -m pip install -r requirements-tts.txt")
    config_path = args.config.expanduser()
    config = {}
    if not os.environ.get("DOUBAO_TTS_API_KEY"):
        if not config_path.is_file():
            parser.error("Provide --config or DOUBAO_TTS_API_KEY; see config/doubao-tts.example.json")
        if os.name != "nt" and stat.S_IMODE(config_path.stat().st_mode) & 0o077:
            parser.error("Credential file must not be readable by group/others (use mode 0600).")
        config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("endpoint", ENDPOINT) != ENDPOINT:
        parser.error("Configured endpoint is not the verified Doubao V3 SSE endpoint.")
    key = os.environ.get("DOUBAO_TTS_API_KEY") or config.get("api_key")
    if not isinstance(key, str) or not key.strip() or key.strip() == "YOUR_API_KEY":
        parser.error("Credential config has no API key.")
    request_id = str(uuid.uuid4())
    result = {**summary, "request_id": request_id, "status": "uncertain", "request_count": 1}
    out.mkdir(parents=True, exist_ok=True)
    # Exclusive creation is the durable guard, including process interruption.
    with journal.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    save(out / "tts-request.json", {"endpoint": ENDPOINT, "request_id": request_id, "body": body})
    headers = {"Content-Type": "application/json", "X-Api-Key": key,
               "X-Api-Resource-Id": "seed-tts-2.0", "X-Api-Request-Id": request_id}
    started = time.monotonic()
    chunks, events, completed = [], [], False
    try:
        with httpx.Client(timeout=httpx.Timeout(240, connect=30), follow_redirects=False) as client:
            with client.stream("POST", ENDPOINT, headers=headers, json=body) as response:
                result["http_status"] = response.status_code
                result["log_id"] = response.headers.get("x-tt-logid")
                response.raise_for_status()
                event_name = None
                for line in response.iter_lines():
                    if line.startswith("event:"):
                        event_name = line[6:].strip()
                    if not line.startswith("data:"):
                        continue
                    event = json.loads(line[5:].strip())
                    code = event.get("code", 0)
                    raw = base64.b64decode(event["data"], validate=True) if event.get("data") else b""
                    if raw:
                        chunks.append(raw)
                    events.append({"event": event_name, "code": code, "audio_bytes": len(raw)})
                    if code not in (0, 20000000):
                        result["provider_code"] = code
                        raise RuntimeError("Provider returned an error code")
                    completed = completed or code == 20000000
        if not completed or not chunks:
            raise RuntimeError("Missing successful completion or audio")
        pcm = b"".join(chunks)
        if len(pcm) % 2:
            raise RuntimeError("Invalid PCM16 length")
        (out / "vo-source.pcm").write_bytes(pcm)
        with wave.open(str(out / "vo-full.wav"), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(44100)
            wav.writeframes(pcm)
        result.update(status="success", duration_ms=round(len(pcm) / 2 / 44100 * 1000),
                      channels=1, sample_frames=len(pcm) // 2,
                      audio_sha256=hashlib.sha256((out / "vo-full.wav").read_bytes()).hexdigest())
    except Exception as error:
        # Exception text can contain request details; retain only its type and safe status/code above.
        result["error_type"] = type(error).__name__
    finally:
        result["wall_seconds"] = round(time.monotonic() - started, 3)
        result["events"] = events
        save(journal, result)
    print(json.dumps({k: v for k, v in result.items() if k != "events"}, ensure_ascii=False))
    if result["status"] != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
