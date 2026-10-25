"""Build the downloadable skill without local environments, models or website sources."""
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import hashlib


def main():
    root = Path(__file__).resolve().parents[1]
    destination = root / "docs/downloads/file-converter.zip"
    destination.parent.mkdir(parents=True, exist_ok=True)
    files = [root / name for name in ["SKILL.md", "README.md", "LICENSE", "requirements.txt",
                                     "requirements-extended.txt", "requirements-professional.txt"]]
    for folder in ["scripts", "references", "tests"]:
        files.extend(path for path in (root / folder).rglob("*") if path.is_file()
                     and "__pycache__" not in path.parts and path.suffix in {".py", ".md", ".txt"}
                     and path.name not in {"package_skill.py", "check_site.py"})
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        for path in sorted(files):
            entry = ZipInfo(path.relative_to(root).as_posix(), date_time=(2026, 10, 25, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            entry.create_system = 3
            entry.external_attr = 0o644 << 16
            archive.writestr(entry, path.read_text(encoding="utf-8").encode("utf-8"))
    with ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert "SKILL.md" in archive.namelist()
    (destination.parent / "SHA256SUMS.txt").write_text(
        hashlib.sha256(destination.read_bytes()).hexdigest() + "  " + destination.name + "\n", encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()
