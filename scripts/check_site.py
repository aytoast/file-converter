"""Check published assets, CLI route syntax, relative links and skill archive."""
import ast
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        self.links.extend(value for key, value in attrs if key in {"href", "src"} and value)


def main():
    tree = ast.parse((ROOT / "scripts/convert.py").read_text(encoding="utf-8"))
    flags, targets = set(), set()
    constants = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
            for name in node.targets:
                if isinstance(name, ast.Name):
                    constants[name.id] = {ast.literal_eval(key) for key in node.value.keys}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
            option = ast.literal_eval(node.args[0])
            flags.add(option)
            if option == "--format":
                choices = next(item.value for item in node.keywords if item.arg == "choices")
                for item in choices.elts:
                    if isinstance(item, ast.Starred):
                        targets.update(constants[item.value.id])
                    else:
                        targets.add(ast.literal_eval(item))
    catalog = json.loads((DOCS / "routes.json").read_text(encoding="utf-8"))
    ids = [source["id"] for source in catalog["sources"]]
    assert len(ids) == len(set(ids)), "Duplicate source IDs"
    count = 0
    for source in catalog["sources"]:
        for route in source["routes"]:
            assert route["target"] in targets, (source["id"], route["target"])
            assert route["note"] and route["dependency"]
            assert route["status"] in {"ready", "unverified"}
            for word in route["flags"].split():
                if word.startswith("--"):
                    assert word in flags, word
            count += 1
    for path in DOCS.rglob("*.html"):
        parser = Links()
        parser.feed(path.read_text(encoding="utf-8"))
        for link in parser.links:
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (path.parent / unquote(parsed.path)).resolve()
            assert target.is_relative_to(DOCS), (path.name, link)
            assert target.exists(), (path.name, link)
    package = DOCS / "downloads/file-converter.zip"
    with ZipFile(package) as archive:
        assert archive.testzip() is None
        assert {"SKILL.md", "scripts/convert.py", "LICENSE"}.issubset(archive.namelist())
        assert not any(name.startswith((".cache/", ".venv/", "node_modules/")) for name in archive.namelist())
        for name in archive.namelist():
            source = ROOT / name
            assert source.resolve().is_relative_to(ROOT)
            assert archive.read(name) == source.read_text(encoding="utf-8").encode("utf-8"), name
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    assert (package.parent / "SHA256SUMS.txt").read_text().startswith(digest)
    print(f"Site checked: {len(ids)} sources, {count} routes; links, CLI flags and ZIP verified")


if __name__ == "__main__":
    main()
