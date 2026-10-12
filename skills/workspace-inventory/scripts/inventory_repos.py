"""Inventory every project folder under a root directory. Read-only.

Usage:
    python inventory_repos.py ROOT [--owner USER,ORG] [--stale-days 180] [--format md|json|csv]

For each immediate subfolder it gathers evidence (git remote, last commit,
uncommitted changes, root commit, entry points, manifests, file mix, README
size) and suggests a status: active, dormant, duplicate, vendored, stub, empty
or not-a-project. Suggestions are evidence for a person or agent to confirm,
not verdicts. Prints to stdout and writes nothing. Runs `git` read-only
commands; makes no network calls.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

JUNK_DIRS = {".git", "node_modules", ".venv", "venv", "env", "__pycache__", ".mypy_cache",
             ".pytest_cache", ".ruff_cache", "dist", "build", "target", ".next", ".idea",
             "archive", "site-packages", ".tox", "coverage"}
CODE_EXT = {".py": "python", ".js": "node", ".ts": "node", ".tsx": "node", ".jsx": "node",
            ".java": "java", ".go": "go", ".rs": "rust", ".cs": "dotnet", ".php": "php",
            ".rb": "ruby", ".html": "html", ".bat": "batch", ".ps1": "powershell", ".sh": "shell"}
ENTRY_FILES = ["app.py", "main.py", "run.py", "server.py", "manage.py", "cli.py", "index.js",
               "server.js", "index.html", "Makefile", "Dockerfile", "docker-compose.yml"]
MAX_FILES_PER_REPO = 20000


def git(repo: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                             timeout=30, encoding="utf-8", errors="replace")
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def scan_files(folder: Path) -> tuple[Counter, float, int]:
    exts: Counter = Counter()
    newest = 0.0
    count = 0
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = [d for d in dirnames if d not in JUNK_DIRS and not d.endswith(".egg-info")]
        for name in filenames:
            count += 1
            if count > MAX_FILES_PER_REPO:
                return exts, newest, count
            path = os.path.join(dirpath, name)
            ext = os.path.splitext(name)[1].lower()
            if ext in CODE_EXT:
                exts[CODE_EXT[ext]] += 1
            try:
                newest = max(newest, os.path.getmtime(path))
            except OSError:
                pass
    return exts, newest, count


def read_text(path: Path, limit: int = 200_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def detect_stack(folder: Path, exts: Counter) -> str:
    parts = []
    deps = (read_text(folder / "requirements.txt") + read_text(folder / "pyproject.toml")).lower()
    if exts.get("python"):
        framework = next((f for f in ("django", "flask", "fastapi", "streamlit") if re.search(rf"\b{f}\b", deps)), "")
        if (folder / "manage.py").exists():
            framework = "django"
        parts.append("python" + (f"/{framework}" if framework else ""))
    package = folder / "package.json"
    if package.exists():
        text = read_text(package).lower()
        framework = next((f for f in ("next", "react", "express", "vue", "svelte") if f'"{f}"' in text), "")
        parts.append("node" + (f"/{'nextjs' if framework == 'next' else framework}" if framework else ""))
    manifest = folder / "manifest.json"
    if manifest.exists() and "manifest_version" in read_text(manifest):
        parts.append("chrome-extension")
    if not parts:
        top = exts.most_common(1)
        parts.append({"html": "static-html"}.get(top[0][0], top[0][0]) if top else "none")
    return " + ".join(parts)


def uv_stub_main(folder: Path) -> bool:
    text = read_text(folder / "main.py", 2000)
    return bool(re.search(r'print\("Hello from [^"]+!"\)', text)) and len(text) < 300


def inspect(folder: Path, owners: list[str], stale_days: int) -> dict:
    exts, newest_mtime, file_count = scan_files(folder)
    is_git = (folder / ".git").exists()
    remote = git(folder, "remote", "get-url", "origin") if is_git else None
    last_commit = git(folder, "log", "-1", "--format=%cI") if is_git else None
    root_commit = git(folder, "rev-list", "--max-parents=0", "HEAD") if is_git else None
    # Tracked edits only: untracked files are often generated in bulk (scaffolders, caches).
    dirty = git(folder, "status", "--porcelain", "--untracked-files=no") if is_git else None
    untracked = git(folder, "ls-files", "--others", "--exclude-standard") if is_git else None
    readme = next((p for p in folder.glob("README*") if p.is_file()), None)
    entries = [name for name in ENTRY_FILES if (folder / name).exists()]
    record = {
        "name": folder.name,
        "path": str(folder),
        "git": is_git,
        "remote": remote or ("local-only" if is_git else None),
        "last_commit": last_commit,
        "root_commit": (root_commit or "").splitlines()[0] if root_commit else None,
        "uncommitted": len(dirty.splitlines()) if dirty else 0,
        "untracked": len(untracked.splitlines()) if untracked else 0,
        "last_modified": time.strftime("%Y-%m-%d", time.localtime(newest_mtime)) if newest_mtime else None,
        "files": file_count if file_count <= MAX_FILES_PER_REPO else f">{MAX_FILES_PER_REPO}",
        "code_files": sum(exts.values()),
        "stack": detect_stack(folder, exts),
        "entry_points": entries,
        "readme_bytes": readme.stat().st_size if readme else 0,
        "uv_stub_main": uv_stub_main(folder),
        "notes": [],
    }
    if record["uv_stub_main"]:
        record["notes"].append("main.py is the uv init stub; the real entry point is elsewhere")
    if readme and record["readme_bytes"] < 200:
        record["notes"].append("README is nearly empty")

    # Git repos are aged by last commit (or count as active with uncommitted work):
    # bulk tools that touch every folder reset file mtimes, so mtime overstates activity.
    newest = newest_mtime
    if last_commit:
        try:
            newest = time.mktime(time.strptime(last_commit[:19], "%Y-%m-%dT%H:%M:%S"))
        except ValueError:
            pass
        if record["uncommitted"]:
            newest = max(newest, newest_mtime)
    age_days = (time.time() - newest) / 86400 if newest else None

    if file_count == 0:
        status = "empty"
    elif record["code_files"] == 0:
        status = "not-a-project"
    elif record["code_files"] <= 2 and not entries:
        status = "stub"
    elif owners and remote and remote != "local-only" and not any(
            f"/{o}/" in remote.lower().replace(":", "/") + "/" for o in owners):
        status = "vendored"
    elif age_days is not None and age_days > stale_days:
        status = "dormant"
    else:
        status = "active"
    record["suggested_status"] = status
    return record


def mark_duplicates(records: list[dict]) -> None:
    groups: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        key = rec["root_commit"] or (rec["remote"] if rec["remote"] not in (None, "local-only") else None)
        if key:
            groups[key].append(rec)
    for members in groups.values():
        if len(members) < 2:
            continue
        members.sort(key=lambda r: (r["last_commit"] or "", r["last_modified"] or ""), reverse=True)
        primary = members[0]
        for rec in members[1:]:
            rec["suggested_status"] = "duplicate"
            rec["duplicate_of"] = primary["name"]
            rec["notes"].append(f"same history as {primary['name']} (newer)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", type=Path)
    parser.add_argument("--owner", default="",
                        help="comma-separated git host users/orgs that are yours; other owners are marked vendored")
    parser.add_argument("--stale-days", type=int, default=180)
    parser.add_argument("--format", choices=["md", "json", "csv"], default="md")
    args = parser.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        return 2
    folders = sorted((p for p in root.iterdir() if p.is_dir() and p.name not in JUNK_DIRS),
                     key=lambda p: p.name.lower())
    records = []
    for i, folder in enumerate(folders, 1):
        print(f"[{i}/{len(folders)}] {folder.name}", file=sys.stderr)
        owners = [o.strip().lower() for o in args.owner.split(",") if o.strip()]
        records.append(inspect(folder, owners, args.stale_days))
    mark_duplicates(records)

    if args.format == "json":
        json.dump(records, sys.stdout, indent=2)
        print()
    elif args.format == "csv":
        fields = ["name", "suggested_status", "duplicate_of", "stack", "remote", "last_commit",
                  "last_modified", "uncommitted", "code_files", "entry_points", "readme_bytes", "notes", "path"]
        writer = csv.DictWriter(sys.stdout, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for rec in records:
            row = {**rec, "entry_points": " ".join(rec["entry_points"]), "notes": "; ".join(rec["notes"])}
            writer.writerow({k: ("'" + v if isinstance(v, str) and v and v[0] in "=+-@" else v) for k, v in row.items()})
    else:
        print("| name | status | stack | last commit | uncommitted | entry points | notes |")
        print("|---|---|---|---|---|---|---|")
        for rec in records:
            status = rec["suggested_status"] + (f" of {rec['duplicate_of']}" if rec.get("duplicate_of") else "")
            print(f"| {rec['name']} | {status} | {rec['stack']} | {(rec['last_commit'] or '')[:10]} | "
                  f"{rec['uncommitted']} | {' '.join(rec['entry_points'])} | {'; '.join(rec['notes'])} |")
    counts = Counter(rec["suggested_status"] for rec in records)
    print("Summary: " + ", ".join(f"{k} {v}" for k, v in counts.most_common()), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
