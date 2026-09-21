"""Behavioral checks for portability, preservation, timing and external-request guards."""
from contextlib import redirect_stdout
from fractions import Fraction
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from align_audio import align
from captions_to_srt import convert
from common import frame_at, final_frame, read_json, sha256
from init_project import initialize
from install import install
from template_payload import instantiate
import synthesize_doubao


class WorkflowTests(unittest.TestCase):
    def fixture(self):
        return read_json(ROOT / "examples/quickstart/acoustic-fixture.json")

    def test_silence_and_frame_handoff(self):
        data = align("先查资料，再回答。", self.fixture(), ["先查资料，", "再回答。"])
        self.assertEqual(data["shared_boundaries_ms"], [0, 1150, 2500])
        self.assertEqual(data["shared_boundaries_frames"], [0, 35, 75])
        self.assertEqual([(p["start_ms"], p["end_ms"]) for p in data["phrases"]], [(200, 1000), (1300, 2200)])

    def test_rational_frame_rounding_and_audio_tail(self):
        self.assertEqual(frame_at(50, "30"), 2)
        self.assertEqual(final_frame(1001, "30000/1001"), 30)
        self.assertEqual(final_frame(1002, "30000/1001"), 31)

    def test_mismatch_is_never_silently_repaired(self):
        data = self.fixture()
        data["words"][1]["text"] = "再回家"
        with self.assertRaisesRegex(ValueError, "needs review"):
            align("先查资料，再回答。", data, ["先查资料，", "再回答。"])

    def test_explicit_review_preserves_original_asr(self):
        data = self.fixture()
        data["words"][1].update(text="再回达", reviewed_text="再回答")
        result = align("先查资料，再回答。", data, ["先查资料，", "再回答。"])
        self.assertEqual(data["words"][1]["text"], "再回达")
        self.assertEqual(result["phrases"][1]["start_ms"], 1300)

    def test_numeric_meaning_is_preserved(self):
        for approved, altered in [("预算是1.5万元。", "预算是15万元。"),
                                  ("变化为-5%。", "变化为5%。"),
                                  ("比例是1/2。", "比例是12。"),
                                  ("需要50%。", "需要50。")]:
            asr = {"duration_ms": 2000, "words": [{"text": altered, "start_ms": 100, "end_ms": 1900}]}
            with self.subTest(approved=approved, location="ASR"):
                with self.assertRaisesRegex(ValueError, "needs review"):
                    align(approved, asr, [approved])
            with self.subTest(approved=approved, location="phrases"):
                with self.assertRaisesRegex(ValueError, "Phrases must cover"):
                    align(approved, asr, [altered])
        asr = {"duration_ms": 2000, "words": [{"text": "预算是1.5万元", "start_ms": 100, "end_ms": 1900}]}
        self.assertEqual(align("预算是1.5万元。", asr, ["预算是1.5万元。"]) ["phrases"][0]["text"], "预算是1.5万元。")

    def test_no_fabricated_subword_timing(self):
        with self.assertRaisesRegex(ValueError, "splits an ASR word"):
            align("先查资料，再回答。", self.fixture(), ["先查", "资料，", "再回答。"])

    def test_overlap_and_tail_errors(self):
        for start, end in [(900, 2200), (1300, 2600)]:
            data = self.fixture()
            data["words"][1].update(start_ms=start, end_ms=end)
            with self.assertRaises(ValueError):
                align("先查资料，再回答。", data, ["先查资料，", "再回答。"])

    def test_final_card_punctuation_and_rational_fps(self):
        srt = convert({"fps": "30000/1001", "cards": [{"text": "App，还用拼音吗？", "start_frame": 30, "end_frame": 60}]})
        self.assertIn("00:00:01,001 --> 00:00:02,002", srt)
        self.assertIn("App，还用拼音吗？", srt)

    def test_overlapping_final_cards_rejected(self):
        with self.assertRaises(ValueError):
            convert({"fps": 30, "cards": [{"text": "甲", "start_frame": 0, "end_frame": 30}, {"text": "乙", "start_frame": 29, "end_frame": 60}]})

    def test_new_project_preserves_inputs_and_has_no_fake_verification(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = root / "原稿.txt"
            script.write_text("先查资料，再回答。\n", encoding="utf-8")
            audio = root / "audio.wav"
            with wave.open(str(audio), "wb") as out:
                out.setnchannels(1); out.setsampwidth(2); out.setframerate(16000)
                out.writeframes(b"\0\0" * 16000)
            dest = root / "新 视频"
            state = initialize(script, dest, audio=audio)
            self.assertEqual(sha256(script), sha256(dest / "script.txt"))
            self.assertEqual(sha256(audio), sha256(dest / state["voice"]["path"]))
            self.assertEqual(state["voice"]["duration_ms"], 1000)
            self.assertFalse(any(state["verification"].values()))
            with self.assertRaises(FileExistsError):
                initialize(script, dest)

    def test_install_refuses_overwrite_and_preserves_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "skills with spaces" / "line-figure-knowledge-video"
            install(dest)
            marker = dest / "my-notes.txt"
            marker.write_text("keep me", encoding="utf-8")
            with self.assertRaises(ValueError):
                install(dest)
            self.assertEqual(marker.read_text(), "keep me")
            installed, backup = install(dest, replace=True)
            self.assertEqual((backup / "my-notes.txt").read_text(), "keep me")
            self.assertTrue((installed / "assets/character/reference.jpg").is_file())

    def test_all_templates_have_new_timings_and_dynamic_mode(self):
        for name in ("retrieve-answer", "compare", "branch", "evidence"):
            data = instantiate(name, 240, [4, 70, 160])
            props = {p["key"]: p["defaultValue"] for p in data["properties"]}
            self.assertFalse(props.get("staticPreview", False))
            self.assertEqual(props.get("previewStage", "auto"), "auto")
            self.assertEqual(props.get("beat2", props.get("resultFrame")), 160)
        with self.assertRaisesRegex(ValueError, "cannot finish"):
            instantiate("retrieve-answer", 180, [0, 60, 170])
        with self.assertRaisesRegex(ValueError, "Unknown properties"):
            instantiate("compare", 240, [0, 60, 150], {"project_id": "unwanted"})

    def test_preview_needs_no_config_and_writes_no_audio(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "audio"
            result = subprocess.run([sys.executable, str(ROOT / "scripts/synthesize_doubao.py"), "--script", str(ROOT / "examples/quickstart/script.txt"), "--speaker", "test-only", "--output", str(out), "--config", str(Path(temp) / "missing.json")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["speech_rate"], 15)
            self.assertFalse(out.exists())

    def test_uncertain_request_is_journaled_and_cannot_repeat(self):
        fake_httpx = types.SimpleNamespace(Timeout=lambda *a, **k: None, Client=lambda **k: (_ for _ in ()).throw(TimeoutError("simulated transport failure")))
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "audio"
            argv = ["synthesize_doubao.py", "--script", str(ROOT / "examples/quickstart/script.txt"), "--speaker", "test-only", "--output", str(out), "--synthesize"]
            with patch.dict(sys.modules, {"httpx": fake_httpx}), patch.dict(os.environ, {"DOUBAO_TTS_API_KEY": "dummy-test-key-not-a-real-secret"}), patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit):
                    synthesize_doubao.main()
            self.assertEqual(read_json(out / "tts-attempt.json")["status"], "uncertain")
            self.assertNotIn("dummy-test-key", (out / "tts-request.json").read_text())
            retry = subprocess.run([sys.executable, str(ROOT / "scripts/synthesize_doubao.py"), *argv[1:]], capture_output=True, text=True)
            self.assertNotEqual(retry.returncode, 0)
            self.assertIn("Prior attempt or audio exists", retry.stderr)


if __name__ == "__main__":
    unittest.main()
