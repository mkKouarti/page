#!/usr/bin/env python3
"""
make_digest.py - regenerate digest.txt from the current repo.

Run it from the repo root:  python3 make_digest.py

Rules:
- ALWAYS overwrites digest.txt (open in "w" mode, never appends).
- Works on any repo. If it is a git repo, it lists exactly what git
  tracks plus untracked files, respecting .gitignore. If not, it walks
  the directory skipping the usual junk.
- Text files go in whole. Binary files (fonts, images, pdf, zip...)
  are listed with their size but no content, so the digest stays
  readable and small.
- Files over MAX_FILE_BYTES get truncated with a clear marker, so a
  lockfile or a minified bundle cannot eat the whole digest.
- Never includes digest.txt itself, so the digest cannot recurse.

Output format, made for LLMs:
  1. A header with date, directory name and file count.
  2. A file index: every path with its size and whether it is
     included, binary-skipped or truncated.
  3. One section per text file, fenced with an unambiguous banner:
     ================================================================
     FILE: relative/path (1.234 bytes)
     ================================================================
"""

import os
import subprocess
import sys
from datetime import datetime, timezone

OUT = "digest.txt"
MAX_FILE_BYTES = 400_000  # per file cap; raise it if you need to

SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "__pycache__",
    ".venv", "venv", "env", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", "dist", "build", ".next", ".cache",
    ".idea", ".vscode",
}

BINARY_EXT = {
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".avif",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".mp3", ".mp4", ".mov", ".avi", ".webm", ".ogg", ".wav", ".flac",
    ".so", ".dll", ".dylib", ".exe", ".bin", ".o", ".a",
    ".pyc", ".pyo", ".class", ".jar", ".wasm",
    ".sqlite", ".db", ".ds_store",
}


def git_files():
    """File list from git: tracked + untracked, .gitignore respected."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            capture_output=True, text=True, check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return [line for line in out.splitlines() if line]


def walk_files():
    """Fallback for non-git directories."""
    found = []
    for root, dirs, names in os.walk("."):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in names:
            found.append(os.path.relpath(os.path.join(root, name)))
    return found


def is_binary(path):
    if os.path.splitext(path)[1].lower() in BINARY_EXT:
        return True
    try:
        with open(path, "rb") as fh:
            return b"\0" in fh.read(8192)
    except OSError:
        return True


def read_text(path):
    """Return (text, truncated). Bytes over the cap are dropped."""
    with open(path, "rb") as fh:
        raw = fh.read(MAX_FILE_BYTES + 1)
    truncated = len(raw) > MAX_FILE_BYTES
    if truncated:
        raw = raw[:MAX_FILE_BYTES]
    return raw.decode("utf-8", errors="replace"), truncated


def main():
    files = git_files()
    source = "git ls-files (tracked + untracked, .gitignore respected)"
    if files is None:
        files = walk_files()
        source = "directory walk (no git repo detected)"

    files = sorted(
        f for f in files
        if os.path.isfile(f) and os.path.basename(f) != OUT
    )

    banner = "=" * 72
    index = []
    sections = []
    for path in files:
        size = os.path.getsize(path)
        if is_binary(path):
            index.append(f"  {path}  ({size:,} bytes)  [binary, content skipped]")
            continue
        text, truncated = read_text(path)
        mark = "  [TRUNCATED]" if truncated else ""
        index.append(f"  {path}  ({size:,} bytes){mark}")
        body = text if text.endswith("\n") or not text else text + "\n"
        if truncated:
            body += f"\n[... truncated at {MAX_FILE_BYTES:,} bytes ...]\n"
        sections.append(f"{banner}\nFILE: {path}  ({size:,} bytes){mark}\n{banner}\n{body}")

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    header = (
        f"REPO DIGEST\n"
        f"directory: {os.path.basename(os.getcwd())}\n"
        f"generated: {stamp}\n"
        f"file list source: {source}\n"
        f"files listed: {len(files)}\n\n"
        f"FILE INDEX\n" + "\n".join(index) + "\n\n"
    )

    # "w" mode: truncates the file first. Whatever digest.txt held is gone.
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(header)
        fh.write("\n".join(sections))

    print(f"wrote {OUT}: {len(files)} files indexed, "
          f"{sum(1 for s in sections)} with full content, "
          f"{os.path.getsize(OUT):,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
