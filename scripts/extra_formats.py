"""Structured text, subtitles, ebooks, fonts and archive repacking."""
import importlib.util
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import tarfile
import zipfile


def pandoc_path():
    executable = shutil.which("pandoc")
    if executable:
        return executable
    if importlib.util.find_spec("pypandoc"):
        import pypandoc
        try:
            return pypandoc.get_pandoc_path()
        except OSError:
            return None
    return None


def structured(source, workspace, target, args):
    import yaml
    raw = source.read_text(encoding=args.encoding, errors="strict")
    if source.suffix.lower() == ".json":
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("Duplicate JSON keys cannot be converted without a policy")
                result[key] = value
            return result
        content = json.loads(raw, object_pairs_hook=unique)
    else:
        class UniqueLoader(yaml.SafeLoader):
            pass
        def mapping(loader, node):
            pairs = loader.construct_pairs(node, deep=True)
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("Duplicate YAML keys cannot be converted without a policy")
                result[key] = value
            return result
        UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
        content = yaml.load(raw, Loader=UniqueLoader)
    # JSON data model is the common subset; rejects dates, binary and other YAML-only values.
    encoded = json.dumps(content, ensure_ascii=False, allow_nan=False)
    normalized = json.loads(encoded)
    output = workspace / f"converted.{target}"
    if target == "json":
        output.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
        json.loads(output.read_text(encoding="utf-8"))
    else:
        output.write_text(yaml.safe_dump(normalized, allow_unicode=True, sort_keys=False), encoding="utf-8")
        if yaml.safe_load(output.read_text(encoding="utf-8")) != normalized:
            raise ValueError("YAML verification failed")
    return [output], ["Comments and formatting are not retained; JSON-compatible values only"], "structured_data_roundtrip_checked"


def subtitles(source, workspace, target, args):
    import pysubs2
    tracks = pysubs2.load(str(source), encoding=args.encoding)
    output = workspace / f"converted.{target}"
    tracks.save(str(output), encoding="utf-8", format_=target)
    check = pysubs2.load(str(output), encoding="utf-8")
    if len(check.events) != len(tracks.events):
        raise ValueError("Subtitle event count changed")
    warnings = ["Subtitle styling and positioning may be reduced in simpler target formats"]
    return [output], warnings, "subtitle_events_reopened"


def content_document(source, workspace, target, args):
    source_type = {".md": "markdown", ".markdown": "markdown", ".html": "html", ".htm": "html",
                   ".txt": "markdown", ".epub": "epub", ".docx": "docx", ".odt": "odt"}.get(source.suffix.lower())
    if target == "pdf" and source.suffix.lower() == ".epub":
        import pymupdf
        output = workspace / "converted.pdf"
        with pymupdf.open(source) as book:
            output.write_bytes(book.convert_to_pdf())
        from document_formats import verify
        verify(output)
        return [output], ["EPUB reflowed to pages; pagination differs from original readers"], "ebook_pdf_reopened"
    if target == "pdf":
        intermediate = workspace / "docx-stage"
        intermediate.mkdir()
        paths, warnings, _ = content_document(source, intermediate, "docx", args)
        from document_formats import office_convert
        outputs, engine_warnings, validation = office_convert(paths[0], workspace, "pdf")
        return outputs, warnings + engine_warnings, validation
    executable = pandoc_path()
    if not executable or not source_type:
        raise ValueError("This document conversion requires Pandoc")
    output_type = {"md": "markdown", "txt": "plain", "html": "html", "docx": "docx",
                   "odt": "odt", "epub": "epub"}.get(target)
    if not output_type:
        raise ValueError("Unsupported content-document target")
    output = workspace / f"converted.{target}"
    process = subprocess.run([executable, "--sandbox", "--from", source_type, "--to", output_type,
                              "--standalone", str(source), "--output", str(output)], capture_output=True, timeout=120)
    if process.returncode:
        raise ValueError("Pandoc failed: " + process.stderr.decode("utf-8", "replace")[-1000:])
    if not output.exists() or not output.stat().st_size:
        raise ValueError("No document output")
    if target in {"docx", "odt"}:
        from document_formats import verify
        verify(output)
    elif target == "epub":
        with zipfile.ZipFile(output) as book:
            if book.read("mimetype") != b"application/epub+zip":
                raise ValueError("Invalid EPUB package")
    return [output], ["Semantic content conversion, not a layout-preserving export; external resources are sandboxed"], "content_document_checked"


def svg(source, workspace, target, args):
    import pymupdf
    output = workspace / f"converted.{target}"
    with pymupdf.open(source) as document:
        if target == "pdf":
            output.write_bytes(document.convert_to_pdf())
        elif target in {"png", "jpg"}:
            document[0].get_pixmap(matrix=pymupdf.Matrix(args.dpi / 72, args.dpi / 72),
                                   alpha=(target == "png")).save(output)
        else:
            raise ValueError("SVG can be rendered to PNG, JPG or PDF")
    return [output], ["SVG rendered; unsupported filters and missing fonts may change appearance"], "svg_rendered"


def font(source, workspace, target, font_index=None):
    from fontTools.ttLib import TTFont
    output = workspace / f"converted.{target}"
    if source.suffix.lower() in {".ttc", ".otc"} and font_index is None:
        raise ValueError("Font collection needs an explicit --font-index")
    with TTFont(source, fontNumber=font_index if font_index is not None else -1) as document:
        original = "otf" if document.sfntVersion == "OTTO" else "ttf"
        if target in {"ttf", "otf"} and target != original:
            raise ValueError("Outline conversion is not implemented; select the source outline type")
        document.flavor = target if target in {"woff", "woff2"} else None
        glyphs = document.getGlyphOrder()
        document.save(output)
    with TTFont(output) as check:
        if check.getGlyphOrder() != glyphs:
            raise ValueError("Font glyph verification failed")
    return [output], ["Font container conversion; licensing and embedding permissions remain unchanged"], "font_glyphs_reopened"


def safe_name(name):
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(piece in {"..", ""} or ":" in piece for piece in path.parts):
        raise ValueError("Archive contains an unsafe path")
    return path


def archives(source, workspace, target):
    extracted = workspace / "contents"
    extracted.mkdir()
    limit = 2 * 1024 ** 3
    count = total = 0
    if zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as archive:
            members = archive.infolist()
            seen = set()
            for info in members:
                relative = safe_name(info.filename)
                identity = str(relative).casefold()
                if identity in seen:
                    raise ValueError("Archive has duplicate or case-conflicting names")
                seen.add(identity)
                if stat.S_ISLNK(info.external_attr >> 16):
                    raise ValueError("Archive symlinks are not supported")
                total += info.file_size
                if total > limit or len(members) > 100000:
                    raise ValueError("Archive exceeds prototype extraction limits")
            for info in members:
                destination = extracted.joinpath(*safe_name(info.filename).parts)
                if info.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(info) as reader, destination.open("xb") as writer:
                        shutil.copyfileobj(reader, writer)
    elif tarfile.is_tarfile(source):
        with tarfile.open(source) as archive:
            for info in archive:
                count += 1
                relative = safe_name(info.name)
                if not (info.isfile() or info.isdir()):
                    raise ValueError("Archive links and special files are unsupported")
                total += info.size
                if total > limit or count > 100000:
                    raise ValueError("Archive exceeds prototype extraction limits")
                destination = extracted.joinpath(*relative.parts)
                if info.isdir():
                    destination.mkdir(parents=True, exist_ok=True)
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with archive.extractfile(info) as reader, destination.open("xb") as writer:
                        shutil.copyfileobj(reader, writer)
    elif source.suffix.lower() == ".7z":
        import py7zr
        with py7zr.SevenZipFile(source) as archive:
            members = archive.list()
            seen = set()
            for info in members:
                relative = safe_name(info.filename)
                identity = str(relative).casefold()
                if identity in seen:
                    raise ValueError("Archive has duplicate or case-conflicting names")
                seen.add(identity)
                if info.is_symlink or not (info.is_file or info.is_directory):
                    raise ValueError("Archive links and special files are unsupported")
                total += info.uncompressed
                if total > limit or len(members) > 100000:
                    raise ValueError("Archive exceeds prototype extraction limits")
            archive.extractall(extracted)
    else:
        raise ValueError("Archive input supports ZIP, 7Z and TAR families")
    output = workspace / ("converted." + target)
    files = sorted(extracted.rglob("*"))
    if target == "zip":
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for item in files:
                archive.write(item, item.relative_to(extracted).as_posix())
        with zipfile.ZipFile(output) as archive:
            if archive.testzip() is not None:
                raise ValueError("Archive CRC verification failed")
    elif target == "7z":
        import py7zr
        with py7zr.SevenZipFile(output, "w") as archive:
            for item in files:
                if item.is_file():
                    archive.write(item, item.relative_to(extracted).as_posix())
        with py7zr.SevenZipFile(output) as archive:
            if archive.test() is False:
                raise ValueError("7Z checksum verification failed")
    else:
        mode = {"tar": "w", "tar.gz": "w:gz", "tar.xz": "w:xz"}.get(target)
        if not mode:
            raise ValueError("Unsupported archive target")
        with tarfile.open(output, mode) as archive:
            for item in files:
                archive.add(item, arcname=item.relative_to(extracted).as_posix(), recursive=False)
        with tarfile.open(output) as archive:
            for item in archive:
                if item.isfile():
                    with archive.extractfile(item) as reader:
                        while reader.read(1024 * 1024):
                            pass
    return [output], ["Repacked files; permissions, signatures and archive-specific metadata may change"], "archive_integrity_checked"
