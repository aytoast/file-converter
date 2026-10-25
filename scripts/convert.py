"""Local conversion prototype. No installation or shell registration side effects."""
import argparse
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

# Keep imports reliable when tests load this entrypoint by absolute file path.
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

IMAGE_INPUTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".gif", ".ico", ".avif", ".heic", ".heif"}
VIDEO_INPUTS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".wmv", ".flv", ".ts", ".mts", ".m2ts", ".mpeg", ".mpg"}
MEDIA_DEMUXERS = {
    ".wav": "wav", ".mp3": "mp3", ".m4a": "mov", ".aac": "aac",
    ".flac": "flac", ".ogg": "ogg", ".mp4": "mov", ".mov": "mov",
    ".mkv": "matroska", ".webm": "matroska", ".avi": "avi",
    ".opus": "ogg", ".aiff": "aiff", ".aif": "aiff", ".wma": "asf",
    ".wmv": "asf", ".flv": "flv", ".ts": "mpegts", ".mts": "mpegts", ".m2ts": "mpegts",
    ".mpeg": "mpeg", ".mpg": "mpeg",
}
AUDIO_CODECS = {"mp3": ("libmp3lame",), "wav": ("pcm_s16le",), "flac": ("flac",),
                "aac": ("aac",), "m4a": ("aac",), "ogg": ("libvorbis",),
                "opus": ("libopus",), "aiff": ("pcm_s16be",), "wma": ("wmav2",)}
VIDEO_CODECS = {"mp4": ("libx264", "aac"), "mkv": ("libx264", "aac"), "mov": ("libx264", "aac"),
                "webm": ("libvpx-vp9", "libopus"), "avi": ("mpeg4", "libmp3lame"),
                "wmv": ("wmv2", "wmav2"), "flv": ("libx264", "aac"),
                "ts": ("libx264", "aac"), "mpeg": ("mpeg2video", "mp2")}


def ffmpeg_path():
    system = shutil.which("ffmpeg")
    if system:
        return system
    if importlib.util.find_spec("imageio_ffmpeg"):
        import imageio_ffmpeg
        try:
            return imageio_ffmpeg.get_ffmpeg_exe()
        except (RuntimeError, OSError):
            pass
    return None


def run(command):
    result = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True)
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(detail[-1500:] or "Conversion process failed")
    return result.stdout.decode("utf-8", errors="replace")


def capabilities():
    pillow = bool(importlib.util.find_spec("PIL"))
    image_targets = []
    if pillow:
        from PIL import Image
        if importlib.util.find_spec("pillow_heif"):
            import pillow_heif
            pillow_heif.register_heif_opener()
        Image.init()
        image_targets = [target for target, kind in {"png": "PNG", "jpg": "JPEG", "pdf": "PDF",
                         "webp": "WEBP", "bmp": "BMP", "tiff": "TIFF", "gif": "GIF",
                         "ico": "ICO", "avif": "AVIF"}.items() if kind in Image.SAVE]
    ffmpeg = ffmpeg_path()
    media_targets = []
    if ffmpeg:
        try:
            listing = run([ffmpeg, "-hide_banner", "-encoders"])
        except (OSError, ValueError):
            listing = ""
        encoders = {line.split()[1] for line in listing.splitlines()
                    if len(line.split()) >= 2 and len(line.split()[0]) == 6}
        media_targets = [name for name, codecs in {**AUDIO_CODECS, **VIDEO_CODECS}.items()
                         if set(codecs).issubset(encoders)]
    import document_formats
    import extra_formats
    import professional_formats
    has = lambda name: bool(importlib.util.find_spec(name))
    return {"pillow": pillow, "ffmpeg": bool(ffmpeg),
            "image_targets": image_targets, "media_targets": media_targets,
            "office_apps_detected": document_formats.office_paths(),
            "libreoffice": bool(document_formats.libreoffice_path()), "office_com": has("win32com"),
            "pdf": has("pymupdf"), "pdf_to_docx": has("pdf2docx"),
            "xlsx": has("openpyxl"), "xls_read": has("xlrd"), "ods": has("odf"),
            "heic_read": has("pillow_heif"), "pandoc": bool(extra_formats.pandoc_path()),
            "subtitles": has("pysubs2"), "yaml": has("yaml"), "seven_zip_output": has("py7zr"),
            "docx": has("docx"), "pptx": has("pptx"), "font_containers": has("fontTools"),
            "font_brotli": has("brotli") or has("brotlicffi"),
            "ocr": has("rapidocr_onnxruntime"), "asr": has("faster_whisper"),
            "professional": professional_formats.capabilities(),
            "unimplemented": ["RAR input", "RAW", "STEP/IGES solids", "contact/calendar conversion"]}


def image_convert(source, temporary, target, background, all_frames=False):
    from PIL import Image, ImageOps
    formats = {"png": "PNG", "jpg": "JPEG", "webp": "WEBP", "pdf": "PDF",
               "bmp": "BMP", "tiff": "TIFF", "gif": "GIF", "ico": "ICO", "avif": "AVIF"}
    with Image.open(source) as original:
        if getattr(original, "n_frames", 1) != 1:
            if not all_frames or target not in {"gif", "png", "webp", "tiff", "pdf"}:
                raise ValueError("Animated or multi-page images need --all-frames and a multi-frame target")
            from PIL import ImageSequence
            frames, durations = [], []
            for item in ImageSequence.Iterator(original):
                rgba = ImageOps.exif_transpose(item).convert("RGBA")
                if target == "pdf":
                    if rgba.getchannel("A").getextrema()[0] < 255 and background is None:
                        raise ValueError("Transparent input: choose --background white or black")
                    rendered = Image.new("RGB", rgba.size, background or "white")
                    rendered.paste(rgba, mask=rgba.getchannel("A"))
                else:
                    rendered = rgba.copy()
                frames.append(rendered)
                durations.append(item.info.get("duration", 100))
            options = {"save_all": True, "append_images": frames[1:]}
            if target in {"gif", "png", "webp"}:
                options.update(duration=durations, loop=original.info.get("loop", 0))
            frames[0].save(temporary, format=formats[target], **options)
            if target == "pdf":
                import pymupdf
                with pymupdf.open(temporary) as check:
                    if len(check) != len(frames):
                        raise ValueError("Image PDF page count changed")
            else:
                with Image.open(temporary) as check:
                    if getattr(check, "n_frames", 1) != len(frames):
                        raise ValueError("Animation frame count changed; merged identical frames require review")
                    for item in ImageSequence.Iterator(check):
                        item.load()
            return "image_frames_checked"
        if original.mode not in {"1", "L", "LA", "P", "RGB", "RGBA"}:
            raise ValueError("Source color mode requires a color-managed workflow")
        original.load()
        icc = original.info.get("icc_profile")
        corrected = ImageOps.exif_transpose(original)
        rgba = corrected.convert("RGBA")
        transparent = rgba.getchannel("A").getextrema()[0] < 255
        if target in {"jpg", "pdf", "bmp"}:
            if transparent and background is None:
                raise ValueError("Transparent input: choose --background white or black")
            rendered = Image.new("RGB", rgba.size, background or "white")
            rendered.paste(rgba, mask=rgba.getchannel("A"))
        else:
            rendered = rgba if transparent else rgba.convert("RGB")
        options = {}
        if target in {"jpg", "webp"}:
            options["quality"] = 90
        if icc and target != "pdf":
            options["icc_profile"] = icc
        rendered.save(temporary, format=formats[target], **options)
        if target == "pdf":
            with temporary.open("rb") as output:
                if output.read(5) != b"%PDF-":
                    raise ValueError("Invalid PDF header")
            with temporary.open("rb") as output:
                output.seek(max(0, temporary.stat().st_size - 64))
                if b"%%EOF" not in output.read():
                    raise ValueError("Incomplete PDF output")
            validation = "pdf_structure_markers_checked"
        else:
            with Image.open(temporary) as output:
                output.load()
                if (target != "ico" and output.size != rendered.size) or output.format != formats[target]:
                    raise ValueError("Output size or format verification failed")
            validation = "decoded_and_dimensions_checked"
        return validation


def media_convert(source, temporary, target, acknowledge_loss):
    if not acknowledge_loss:
        raise ValueError("Media export retains only first streams and removes metadata; "
                         "confirm this limitation, then pass --allow-media-loss")
    ffmpeg = ffmpeg_path()
    if not ffmpeg:
        raise ValueError("FFmpeg is unavailable")
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
               "-protocol_whitelist", "file,pipe", "-f", MEDIA_DEMUXERS[source.suffix.lower()],
               "-i", str(source), "-map_metadata", "-1", "-map_chapters", "-1"]
    if target in AUDIO_CODECS:
        command += ["-map", "0:a:0", "-vn", "-c:a", AUDIO_CODECS[target][0]]
        if target == "mp3":
            command += ["-q:a", "2"]
        elif target in {"aac", "m4a", "wma", "ogg", "opus"}:
            command += ["-b:a", "192k"]
    else:
        video_codec, audio_codec = VIDEO_CODECS[target]
        command += ["-map", "0:v:0", "-map", "0:a:0?", "-sn", "-dn",
                    "-c:v", video_codec, "-c:a", audio_codec,
                    "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-pix_fmt", "yuv420p"]
        if video_codec == "libx264":
            command += ["-crf", "20", "-preset", "medium"]
        elif video_codec == "libvpx-vp9":
            command += ["-crf", "32", "-b:v", "0"]
        else:
            command += ["-q:v", "3"]
        if target in {"mp4", "mov"}:
            command += ["-movflags", "+faststart"]
    run(command + [str(temporary)])
    run([ffmpeg, "-hide_banner", "-loglevel", "error", "-xerror", "-nostdin",
         "-protocol_whitelist", "file,pipe", "-i", str(temporary),
         "-map", "0", "-f", "null", "-"])
    return "full_output_decode_checked"


def publish(temporary, directory, stem, target):
    for counter in range(10000):
        name = f"{stem}.{target}" if counter == 0 else f"{stem} ({counter}).{target}"
        destination = directory / name
        try:
            handle = destination.open("xb")
        except FileExistsError:
            continue
        try:
            with handle, temporary.open("rb") as source:
                shutil.copyfileobj(source, handle)
                handle.flush()
                os.fsync(handle.fileno())
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
        return destination
    raise ValueError("Too many conflicting output names")


def convert(source, args, available):
    source = source.expanduser().resolve(strict=True)
    if not source.is_file():
        raise ValueError("Input is not a file")
    extension = source.suffix.lower()
    target = args.format
    import table_formats
    import document_formats
    import extra_formats
    import professional_formats
    import cross_formats
    from types import SimpleNamespace
    defaults = {"pages": None, "dpi": 144, "all_frames": False, "sheet": None, "all_sheets": False,
                "formulas": "reject", "encoding": "utf-8-sig", "output_encoding": "utf-8-sig",
                "delimiter": None, "allow_layout_loss": False, "background": None, "output_dir": None,
                "allow_media_loss": False, "start": None, "duration": None, "fps": 10,
                "ocr": False, "asr_model_path": None, "language": None, "layout": "Model", "layer": None,
                "source_crs": None, "target_crs": None, "x_column": None, "y_column": None,
                "geometry_column": None, "font_index": None, "vector_threshold": 128}
    args = SimpleNamespace(**{**defaults, **vars(args)})
    archive_input = source.name.lower().endswith((".zip", ".7z", ".tar", ".tar.gz", ".tgz", ".tar.xz", ".txz"))
    cross_image = extension in IMAGE_INPUTS and (target in {"txt", "md", "docx", "csv", "tsv", "xlsx", "json", "mp4", "svg"} or args.ocr)
    cross_media = extension in MEDIA_DEMUXERS and target in {"txt", "md", "docx", "srt", "vtt", "json", "frames"}
    if cross_image or cross_media:
        kind = "cross"
    elif extension in IMAGE_INPUTS:
        if target not in available["image_targets"]:
            raise ValueError("Image target unsupported or Pillow dependency unavailable")
        kind = "image"
    elif extension in MEDIA_DEMUXERS:
        if target not in available["media_targets"] and not (extension in VIDEO_INPUTS and target in {"png", "jpg", "gif"}):
            raise ValueError("Media target unsupported or required encoder unavailable")
        if target in VIDEO_CODECS and extension not in VIDEO_INPUTS:
            raise ValueError("Audio-only input cannot be converted into video")
        kind = "media"
    else:
        kind = "extended"
    directory = Path(args.output_dir).expanduser().resolve() if args.output_dir else source.parent
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".file-converter-", dir=directory) as workspace:
        temporary = Path(workspace) / f"converted.{target}"
        warnings = []
        if kind == "image":
            validation = image_convert(source, temporary, target, args.background, args.all_frames)
            paths = [temporary]
            warnings = ["EXIF metadata removed; verify color, transparency and animation after conversion"]
        elif kind == "media":
            if target in {"png", "jpg", "gif"}:
                validation = video_image_convert(source, temporary, target, args)
            else:
                validation = media_convert(source, temporary, target, args.allow_media_loss)
            paths = [temporary]
            warnings = ["First streams only; metadata and extra tracks removed; odd video dimensions padded to even pixels"]
        elif extension in IMAGE_INPUTS and target == "svg":
            paths, warnings, validation = cross_formats.raster_vector(source, Path(workspace), args)
        elif extension in IMAGE_INPUTS and target == "mp4":
            paths, warnings, validation = cross_formats.images_video([source], Path(workspace), args)
        elif (extension in IMAGE_INPUTS or extension == ".pdf") and args.ocr:
            paths, warnings, validation = cross_formats.ocr(source, Path(workspace), target, args)
        elif extension in IMAGE_INPUTS:
            paths, warnings, validation = cross_formats.ocr(source, Path(workspace), target, args)
        elif extension in MEDIA_DEMUXERS and target == "frames":
            paths, warnings, validation = cross_formats.frames(source, Path(workspace), args)
        elif extension in MEDIA_DEMUXERS:
            paths, warnings, validation = cross_formats.asr(source, Path(workspace), target, args)
        elif target == "images" and extension in {".pdf", ".docx", ".pptx", ".xlsx"}:
            paths, warnings, validation = cross_formats.extract_images(source, Path(workspace))
        elif extension in professional_formats.MODEL_INPUTS:
            paths, warnings, validation = professional_formats.model(source, Path(workspace), target, args)
        elif extension in {".dxf", ".dwg"}:
            paths, warnings, validation = professional_formats.cad(source, Path(workspace), target, args)
        elif extension in professional_formats.GIS_INPUTS or source.name.lower().endswith(".shp.zip") or (
                extension in {".csv", ".xlsx"} and target in professional_formats.GIS_DRIVERS):
            paths, warnings, validation = professional_formats.geo(source, Path(workspace), target, args)
        elif extension == ".pdf":
            paths, warnings, validation = document_formats.pdf_convert(source, Path(workspace), target, args)
        elif extension in {".json", ".yaml", ".yml"} and target in {"json", "yaml", "yml"}:
            paths, warnings, validation = extra_formats.structured(source, Path(workspace), target, args)
        elif extension in {".xls", ".xlsx", ".xlsm", ".ods"} and target in {"xls", "xlsx", "ods"}:
            if extension == ".xlsm" and not args.allow_layout_loss:
                raise ValueError("Macro-enabled workbook export removes macros; choose --allow-layout-loss explicitly")
            paths, warnings, validation = document_formats.office_convert(source, Path(workspace), target)
        elif extension in table_formats.INPUTS and target in table_formats.TARGETS:
            paths, warnings, validation = table_formats.convert(source, Path(workspace), target, args)
        elif extension == ".docx" and target in {"txt", "md", "html"}:
            paths, warnings, validation = document_formats.docx_text(source, Path(workspace), target)
        elif extension in {".docx", ".odt"} and target == "epub":
            paths, warnings, validation = extra_formats.content_document(source, Path(workspace), target, args)
        elif extension in document_formats.OFFICE_INPUTS and target in {"png", "jpg", "tiff", "svg"}:
            paths, warnings, validation = document_formats.office_images(source, Path(workspace), target, args)
        elif extension in document_formats.OFFICE_INPUTS:
            paths, warnings, validation = document_formats.office_convert(source, Path(workspace), target)
        elif extension in {".md", ".markdown", ".html", ".htm", ".txt", ".epub"}:
            paths, warnings, validation = extra_formats.content_document(source, Path(workspace), target, args)
        elif extension in {".srt", ".vtt", ".ass", ".ssa"} and target in {"srt", "vtt", "ass", "ssa"}:
            paths, warnings, validation = extra_formats.subtitles(source, Path(workspace), target, args)
        elif extension == ".svg":
            paths, warnings, validation = extra_formats.svg(source, Path(workspace), target, args)
        elif extension in {".ttf", ".otf", ".woff", ".woff2", ".ttc", ".otc"} and target in {"ttf", "otf", "woff", "woff2"}:
            paths, warnings, validation = extra_formats.font(source, Path(workspace), target, args.font_index)
        elif archive_input and target in {"zip", "7z", "tar", "tar.gz", "tar.xz"}:
            paths, warnings, validation = extra_formats.archives(source, Path(workspace), target)
        else:
            raise ValueError("Unsupported conversion route")
        published = []
        try:
            for index, item in enumerate(paths):
                if not item.is_file() or (item.stat().st_size == 0 and target not in {"txt", "md", "csv", "tsv", "jsonl", "srt", "vtt"}):
                    raise ValueError("Conversion produced no file")
                stem = source.stem if len(paths) == 1 else source.stem + "_" + item.stem
                actual_target = item.suffix.lstrip(".") if target in {"images", "frames"} else target
                published.append(publish(item, directory, stem, actual_target))
        except BaseException:
            for item in published:
                item.unlink(missing_ok=True)
            raise
        output = published[0]
    return {"input": str(source), "output": str(output), "status": "success",
            "outputs": [str(item) for item in published],
            "bytes": sum(item.stat().st_size for item in published), "validation": validation, "warnings": warnings}


def video_image_convert(source, output, target, args):
    ffmpeg = ffmpeg_path()
    if not ffmpeg:
        raise ValueError("FFmpeg unavailable")
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
               "-protocol_whitelist", "file,pipe", "-ss", str(args.start or 0),
               "-f", MEDIA_DEMUXERS[source.suffix.lower()], "-i", str(source), "-an"]
    if target == "gif":
        if args.duration is None or args.duration <= 0:
            raise ValueError("Video GIF export needs an explicit --duration in seconds")
        command += ["-t", str(args.duration), "-vf", f"fps={args.fps},scale=480:-1:flags=lanczos", "-loop", "0"]
    else:
        command += ["-frames:v", "1"]
    run(command + [str(output)])
    from PIL import Image
    with Image.open(output) as check:
        check.load()
    return "video_image_decoded"


def merge_images(args, available):
    import pymupdf
    sources = [Path(name).expanduser().resolve(strict=True) for name in args.input]
    if args.format not in {"pdf", "mp4"} or not sources or any(item.suffix.lower() not in IMAGE_INPUTS for item in sources):
        raise ValueError("--merge supports explicitly ordered images to PDF or MP4")
    directory = Path(args.output_dir).expanduser().resolve() if args.output_dir else sources[0].parent
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".file-converter-", dir=directory) as workspace:
        if args.format == "mp4":
            import cross_formats
            paths, warnings, validation = cross_formats.images_video(sources, Path(workspace), args)
            output = publish(paths[0], directory, sources[0].stem + "_merged", "mp4")
            return {"inputs": [str(item) for item in sources], "status": "success", "output": str(output),
                    "outputs": [str(output)], "bytes": output.stat().st_size, "validation": validation, "warnings": warnings}
        merged = pymupdf.open()
        for index, source in enumerate(sources):
            page_path = Path(workspace) / f"input-{index}.pdf"
            image_convert(source, page_path, "pdf", args.background, args.all_frames)
            with pymupdf.open(page_path) as document:
                merged.insert_pdf(document)
        total = len(merged)
        temporary = Path(workspace) / "merged.pdf"
        merged.save(temporary)
        merged.close()
        with pymupdf.open(temporary) as check:
            if len(check) != total:
                raise ValueError("Merged PDF page count mismatch")
        output = publish(temporary, directory, sources[0].stem + "_merged", "pdf")
    return {"inputs": [str(item) for item in sources], "status": "success", "output": str(output),
            "outputs": [str(output)], "pages": total, "bytes": output.stat().st_size,
            "validation": "merged_pdf_page_count_checked", "warnings": ["Image PDF without OCR; input order retained"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capabilities", action="store_true")
    parser.add_argument("--targets", action="store_true", help="List dependency-aware targets for --input files")
    parser.add_argument("--input", action="append", default=[])
    parser.add_argument("--format", choices=["png", "jpg", "jpeg", "webp", "pdf", "bmp", "tiff", "gif", "ico", "avif",
                                            *AUDIO_CODECS, *VIDEO_CODECS, "doc", "docx", "odt", "rtf", "txt", "html", "md",
                                            "xls", "xlsx", "ods", "csv", "tsv", "json", "jsonl", "yaml", "yml",
                                            "ppt", "pptx", "odp", "epub", "svg", "srt", "vtt", "ass", "ssa",
                                            "zip", "7z", "tar", "tar.gz", "tar.xz", "ttf", "otf", "woff", "woff2",
                                            "obj", "stl", "ply", "off", "glb", "gltf", "fbx", "blend", "dxf", "dwg",
                                            "geojson", "gpkg", "shp.zip", "kml", "gpx", "fgb", "images", "frames"])
    parser.add_argument("--output-dir")
    parser.add_argument("--background", choices=["white", "black"])
    parser.add_argument("--allow-media-loss", action="store_true")
    parser.add_argument("--all-frames", action="store_true")
    parser.add_argument("--allow-layout-loss", action="store_true")
    parser.add_argument("--sheet")
    parser.add_argument("--all-sheets", action="store_true")
    parser.add_argument("--formulas", choices=["reject", "values", "expressions"], default="reject")
    parser.add_argument("--encoding", default="utf-8-sig")
    parser.add_argument("--output-encoding", default="utf-8-sig")
    parser.add_argument("--delimiter")
    parser.add_argument("--pages")
    parser.add_argument("--dpi", type=int, default=144)
    parser.add_argument("--merge", action="store_true")
    parser.add_argument("--start", type=float)
    parser.add_argument("--duration", type=float)
    parser.add_argument("--fps", type=int, default=10)
    parser.add_argument("--ocr", action="store_true")
    parser.add_argument("--asr-model-path")
    parser.add_argument("--language")
    parser.add_argument("--layout", default="Model")
    parser.add_argument("--layer")
    parser.add_argument("--source-crs")
    parser.add_argument("--target-crs")
    parser.add_argument("--x-column")
    parser.add_argument("--y-column")
    parser.add_argument("--geometry-column")
    parser.add_argument("--font-index", type=int)
    parser.add_argument("--vector-threshold", type=int, default=128)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        with contextlib.redirect_stdout(sys.stderr):
            available = capabilities()
        if args.capabilities:
            print(json.dumps(available, ensure_ascii=False))
            return 0
        if args.targets:
            if not args.input:
                parser.error("--targets needs at least one --input")
            print(json.dumps({"files": [{"input": name, "targets": targets_for(Path(name), available)}
                                         for name in args.input]}, ensure_ascii=False))
            return 0
        if not args.input or not args.format:
            parser.error("--input and --format are required")
        if not 36 <= args.dpi <= 600:
            parser.error("--dpi must be between 36 and 600")
        if not 1 <= args.fps <= 60 or (args.start is not None and args.start < 0):
            parser.error("Invalid --fps or --start")
        if not 0 <= args.vector_threshold <= 255 or (args.font_index is not None and args.font_index < 0):
            parser.error("Invalid vector threshold or font index")
        if args.format == "jpeg":
            args.format = "jpg"
        if args.merge:
            with contextlib.redirect_stdout(sys.stderr):
                merged = merge_images(args, available)
            print(json.dumps({"results": [merged]}, ensure_ascii=False))
            return 0
        results = []
        for name in args.input:
            try:
                with contextlib.redirect_stdout(sys.stderr):
                    converted = convert(Path(name), args, available)
                results.append(converted)
            except Exception as error:
                results.append({"input": name, "status": "failed", "error": str(error)})
        print(json.dumps({"results": results}, ensure_ascii=False))
        return int(any(item["status"] == "failed" for item in results))
    except KeyboardInterrupt:
        print(json.dumps({"status": "cancelled"}))
        return 2
    except Exception as error:
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False))
        return 1


def targets_for(source, available):
    import table_formats
    import document_formats
    import professional_formats
    extension = source.suffix.lower()
    if extension in IMAGE_INPUTS:
        if extension in {".heic", ".heif"} and not available["heic_read"]:
            return []
        names = list(available["image_targets"])
        if available["ocr"]:
            names += ["txt", "md", "json", "docx", "csv", "tsv", "xlsx"]
        if "mp4" in available["media_targets"]:
            names.append("mp4")
        if importlib.util.find_spec("cv2"):
            names.append("svg")
        return names
    if extension in MEDIA_DEMUXERS:
        names = available["media_targets"]
        names = list(names) if extension in VIDEO_INPUTS else [n for n in names if n in AUDIO_CODECS]
        if extension in VIDEO_INPUTS:
            names += ["png", "jpg", "gif", "frames"]
        if available["asr"]:
            names += ["txt", "md", "docx", "srt", "vtt", "json"]
        return names
    if extension == ".pdf":
        if not available["pdf"]:
            return []
        names = ["png", "jpg", "tiff", "svg", "txt", "md", "html", "csv", "tsv", "json", "jsonl"]
        if available["xlsx"]:
            names.append("xlsx")
        if available["pdf_to_docx"] and available["docx"]:
            names.append("docx")
        if available["pptx"]:
            names.append("pptx")
        return names + ["images"] + (["pdf"] if available["ocr"] else [])
    names = []
    pro = available["professional"]
    if extension in professional_formats.MODEL_INPUTS:
        if extension == ".off":
            return ["obj", "stl", "ply", "off", "glb"] if pro["trimesh"] else []
        if pro["blender"]:
            return ["obj", "stl", "ply", "glb", "gltf", "fbx", "blend", "png"]
        return ["obj", "stl", "ply", "off", "glb"] if pro["trimesh"] and extension not in {".fbx", ".blend"} else []
    if extension in {".dxf", ".dwg"}:
        if not pro["dxf"] or (extension == ".dwg" and not pro["oda"]):
            return []
        return ["dxf"] + (["png", "pdf", "svg"] if pro["cad_render"] else []) + (["dwg"] if pro["oda"] else [])
    if extension in professional_formats.GIS_INPUTS or source.name.lower().endswith(".shp.zip"):
        return pro["gis_write_targets"] + ["csv", "xlsx"] if pro["gis"] else []
    readable = (extension not in {".xlsx", ".xlsm", ".xls", ".ods"} or
                available[{".xlsx": "xlsx", ".xlsm": "xlsx", ".xls": "xls_read", ".ods": "ods"}[extension]])
    if extension in table_formats.INPUTS and readable:
        names += ["csv", "tsv", "json", "jsonl", "html"]
        if available["xlsx"]:
            names.append("xlsx")
        if available["ods"]:
            names.append("ods")
        if extension in {".csv", ".xlsx"} and pro["gis"]:
            names += pro["gis_write_targets"]
    if extension in {".json", ".yaml", ".yml"} and available["yaml"]:
        names += ["json", "yaml", "yml"]
    if extension in document_formats.OFFICE_INPUTS:
        kind = "excel" if extension in {".xls", ".xlsx", ".xlsm", ".ods"} else "powerpoint" if extension in {".ppt", ".pptx", ".odp"} else "word"
        native = available["libreoffice"] or (available["office_com"] and available["office_apps_detected"][kind])
        if native:
            names += {"word": ["doc", "docx", "odt", "rtf", "pdf", "txt"],
                      "excel": ["xls", "xlsx", "ods", "pdf"], "powerpoint": ["ppt", "pptx", "odp", "pdf"]}[kind]
            names += ["png", "jpg", "tiff", "svg"]
        elif kind == "excel":
            # Workbook-to-workbook routes require an Office engine to preserve workbook semantics.
            names = [name for name in names if name not in {"xls", "xlsx", "ods"}]
        if extension == ".docx" and available["docx"]:
            names += ["txt", "md", "html"]
        if extension in {".docx", ".pptx", ".xlsx"}:
            names.append("images")
        if extension in {".docx", ".odt"} and available["pandoc"]:
            names.append("epub")
    if extension in {".md", ".markdown", ".html", ".htm", ".txt", ".epub"} and available["pandoc"]:
        names += ["md", "html", "txt", "docx", "odt", "epub"]
        if available["libreoffice"] or (available["office_com"] and available["office_apps_detected"]["word"]):
            names.append("pdf")
    if extension == ".epub" and available["pdf"]:
        names.append("pdf")
    if extension in {".srt", ".vtt", ".ass", ".ssa"} and available["subtitles"]:
        names += ["srt", "vtt", "ass", "ssa"]
    if extension == ".svg" and available["pdf"]:
        names += ["png", "jpg", "pdf"]
    if extension in {".ttf", ".otf", ".woff", ".woff2", ".ttc", ".otc"} and available["font_containers"]:
        names.append("woff")
        if available.get("font_brotli"):
            names.append("woff2")
        if source.is_file():
            with source.open("rb") as font:
                signature = font.read(8)
            if extension in {".ttc", ".otc"}:
                names += ["ttf", "otf"]
            else:
                names.append("otf" if signature[:4] == b"OTTO" or signature[4:8] == b"OTTO" else "ttf")
    if source.name.lower().endswith((".zip", ".7z", ".tar", ".tar.gz", ".tgz", ".tar.xz", ".txz")):
        names += ["zip", "tar", "tar.gz", "tar.xz"]
        if available["seven_zip_output"]:
            names.append("7z")
    return sorted(set(names))


if __name__ == "__main__":
    sys.exit(main())
