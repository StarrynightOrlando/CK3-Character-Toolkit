"""Audit source-only contents, then create a deterministic public ZIP.

No CK3, Blender, network, local settings or private model is needed.
Runtime generated from CK3 is deliberately excluded.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bridge import core

TOP_FILES = {
    "bridge_cli.py", "start.ps1", "启动工具.cmd", ".gitignore",
    ".gitattributes", "README.md", "README.txt", "LICENSE.md",
    "THIRD_PARTY_NOTICES.md", "CHANGELOG.md",
}
SOURCE_DIRS = {"bridge", "docs", "examples", "tests", "tools", ".github"}
SUFFIXES = {".py", ".txt", ".md", ".json", ".html", ".ps1", ".cmd", ".yml", ".yaml"}
SECRET_PATTERNS = (
    r"gh[pousr]_[A-Za-z0-9]{30,}",
    r"github_pat_[A-Za-z0-9_]{30,}",
    r"sk-[A-Za-z0-9_-]{24,}",
    r"AKIA[0-9A-Z]{16}",
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
)


def source_files():
    paths = [ROOT / name for name in TOP_FILES if (ROOT / name).is_file()]
    for folder in SOURCE_DIRS:
        paths.extend(p for p in (ROOT / folder).rglob("*")
                     if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")
    errors = []
    for p in paths:
        rel = p.relative_to(ROOT).as_posix()
        if p.is_symlink() or not p.resolve().is_relative_to(ROOT.resolve()):
            errors.append("Source link/path escape: " + rel)
        if p.name not in TOP_FILES and p.suffix.lower() not in SUFFIXES:
            errors.append("Non-source file: " + rel)
        if ".local." in p.name or any(part.endswith(".local") for part in p.relative_to(ROOT).parts):
            errors.append("Private local file: " + rel)
        try:
            text = p.read_text(encoding="utf-8-sig")
        except (UnicodeError, OSError):
            errors.append("Not UTF-8 text: " + rel)
            continue
        if any(re.search(pattern, text) for pattern in SECRET_PATTERNS):
            errors.append("Possible credential: " + rel)
        for match in re.finditer(r"(?i)[A-Z]:[/\\]+Users[/\\]+([^/\\\s\"']+)", text):
            if match[1] != "YOUR_NAME":
                errors.append("Personal Windows path: " + rel)
        if p.suffix == ".md":
            for link in re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", text):
                if "://" in link or link.startswith("#"):
                    continue
                target = link.split("#", 1)[0]
                if target and not (p.parent / target).exists():
                    errors.append("Broken local Markdown link: " + rel + " -> " + target)
    allowed = {p.relative_to(ROOT).as_posix() for p in paths}
    if (ROOT / ".git").exists():
        tracked = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True,
                                 stdout=subprocess.PIPE).stdout.decode("utf-8").split("\0")
        for name in filter(None, tracked):
            if name not in allowed:
                errors.append("Tracked file outside public whitelist: " + name)
    if errors:
        raise ValueError("\n".join(sorted(set(errors))))
    return sorted(paths, key=lambda p: p.relative_to(ROOT).as_posix())


def main():
    files = source_files()
    expected = {p.relative_to(ROOT).as_posix(): p.read_bytes() for p in files}
    generated = core.public_zip()
    with zipfile.ZipFile(generated) as archive:
        if set(archive.namelist()) != set(expected):
            raise ValueError("public-zip inventory differs from audited source whitelist")
        if any(archive.read(name) != data for name, data in expected.items()):
            raise ValueError("public-zip content differs from audited source")
    release = ROOT / "releases" / "0.5.0-public.1"
    release.mkdir(parents=True, exist_ok=True)
    output = release / "CK3-Character-Toolkit-0.5.0-public.1-source.zip"
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in expected.items():
            info = zipfile.ZipInfo(name, (2026, 10, 4, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    report = {
        "public_source_audit_passed": True,
        "release": "0.5.0-public.1",
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in expected.items()},
        "archive_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "runtime_game_derived_files_included": False,
        "private_assets_included": False,
        "credential_scan": "Known token patterns and personal Windows paths; not proof of all possible secrets",
        "game_visual_verified": False,
    }
    (release / "public-source-audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (release / "SHA256SUMS.txt").write_text(
        report["archive_sha256"] + "  " + output.name + "\n", encoding="utf-8")
    print(json.dumps({"files": len(files), "sha256": report["archive_sha256"],
                      "archive": str(output), "audit_passed": True}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
