import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "convert.py"
spec = importlib.util.spec_from_file_location("converter", SCRIPT)
converter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(converter)


class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory(prefix="converter-tests-")
        self.root = Path(self.workspace.name)
        self.source = self.root / "照片 with spaces & 'quote'.png"
        Image.new("RGB", (32, 24), "red").save(self.source)
        self.original = self.source.read_bytes()

    def tearDown(self):
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(list(self.root.glob(".file-converter-*")), [])
        self.workspace.cleanup()

    def cli(self, *args):
        result = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True)
        payload = json.loads(result.stdout.decode("utf-8"))
        return result.returncode, payload

    def test_image_targets_and_collision(self):
        for target in ["jpg", "png", "webp"]:
            if target not in converter.capabilities()["image_targets"]:
                continue
            for _ in range(2):
                code, payload = self.cli("--input", self.source, "--format", target)
                self.assertEqual(code, 0, payload)
                output = Path(payload["results"][0]["output"])
                self.assertNotEqual(output, self.source)
                with Image.open(output) as image:
                    image.load()
                    self.assertEqual(image.size, (32, 24))

    def test_transparency_requires_explicit_background(self):
        transparent = self.root / "transparent.png"
        Image.new("RGBA", (16, 16), (0, 0, 255, 0)).save(transparent)
        code, payload = self.cli("--input", transparent, "--format", "jpg")
        self.assertEqual(code, 1)
        self.assertIn("background", payload["results"][0]["error"])
        self.assertFalse(transparent.with_suffix(".jpg").exists())
        code, payload = self.cli("--input", transparent, "--format", "jpg", "--background", "white")
        self.assertEqual(code, 0, payload)
        with Image.open(payload["results"][0]["output"]) as output:
            self.assertGreater(min(output.getpixel((8, 8))), 245)

    def test_orientation_and_metadata(self):
        oriented = self.root / "rotated.jpg"
        exif = Image.Exif()
        exif[274] = 6
        exif[315] = "private author"
        Image.new("RGB", (32, 24), "blue").save(oriented, exif=exif)
        code, payload = self.cli("--input", oriented, "--format", "png")
        self.assertEqual(code, 0, payload)
        with Image.open(payload["results"][0]["output"]) as output:
            self.assertEqual(output.size, (24, 32))
            self.assertFalse(output.getexif())

    def test_batch_partial_failure(self):
        broken = self.root / "broken.png"
        broken.write_bytes(b"not an image")
        code, payload = self.cli("--input", broken, "--input", self.source, "--format", "jpg")
        self.assertEqual(code, 1)
        self.assertEqual([x["status"] for x in payload["results"]], ["failed", "success"])
        self.assertEqual(broken.read_bytes(), b"not an image")

    def test_multiframe_rejected(self):
        multipage = self.root / "pages.tiff"
        Image.new("RGB", (8, 8), "red").save(
            multipage, save_all=True, append_images=[Image.new("RGB", (8, 8), "blue")])
        code, payload = self.cli("--input", multipage, "--format", "jpg")
        self.assertEqual(code, 1)
        self.assertIn("multi-page", payload["results"][0]["error"])

    def test_pdf(self):
        code, payload = self.cli("--input", self.source, "--format", "pdf")
        self.assertEqual(code, 0, payload)
        output = Path(payload["results"][0]["output"])
        self.assertTrue(output.read_bytes().startswith(b"%PDF-"))
        if importlib.util.find_spec("pypdf"):
            from pypdf import PdfReader
            self.assertEqual(len(PdfReader(output).pages), 1)

    def test_media_routes_and_loss_acknowledgement(self):
        available = converter.capabilities()
        ffmpeg = converter.ffmpeg_path()
        if not ffmpeg or not {"mp3", "wav", "mp4"}.issubset(available["media_targets"]):
            self.skipTest("FFmpeg encoders unavailable")
        video = self.root / "视频 sample.mp4"
        converter.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i",
                       "color=c=blue:s=32x24:d=0.3", "-f", "lavfi", "-i",
                       "sine=frequency=440:duration=0.3", "-shortest",
                       "-c:v", "libx264", "-c:a", "aac", str(video)])
        original_video = video.read_bytes()
        code, payload = self.cli("--input", video, "--format", "mp3")
        self.assertEqual(code, 1)
        self.assertIn("allow-media-loss", payload["results"][0]["error"])
        for target in ["mp3", "wav", "mp4"]:
            code, payload = self.cli("--input", video, "--format", target, "--allow-media-loss")
            self.assertEqual(code, 0, payload)
            item = payload["results"][0]
            self.assertEqual(item["validation"], "full_output_decode_checked")
            self.assertGreater(item["bytes"], 0)
        self.assertEqual(video.read_bytes(), original_video)


if __name__ == "__main__":
    unittest.main()
