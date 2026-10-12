"""Audit the AI-assistant instruction files in a repository. Read-only.

Usage: python check_agent_files.py [REPO_DIR] [--strict]

Lists every instruction file that a known tool loads, classifies each one
against the canonical AGENTS.md (canonical, import, pointer, copy, diverged),
and flags markdown files sitting in tool folders at paths no tool is known to
read. Exits 1 with --strict when it finds a diverged copy, an orphan file, or
no AGENTS.md. Standard library only; writes nothing.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Files a tool loads, relative to the repo root. Globs allowed. Verify against
# each tool's current docs; conventions change.
KNOWN_FILES: dict[str, str] = {
    "AGENTS.md": "AGENTS.md standard (Codex, Cursor, Copilot agent, Windsurf, Roo, Kilo, Amp, Zed, Jules, Junie, ...)",
    "CLAUDE.md": "Claude Code",
    ".claude/CLAUDE.md": "Claude Code",
    "GEMINI.md": "Gemini CLI",
    ".github/copilot-instructions.md": "GitHub Copilot",
    ".github/instructions/*.instructions.md": "GitHub Copilot (scoped)",
    ".cursorrules": "Cursor (legacy)",
    ".cursor/rules/*.mdc": "Cursor rules",
    ".cursor/rules/*.md": "Cursor rules",
    ".windsurfrules": "Windsurf (legacy)",
    ".windsurf/rules/*.md": "Windsurf rules",
    ".clinerules": "Cline",
    ".clinerules/*.md": "Cline rules",
    ".roorules": "Roo Code (legacy)",
    ".roo/rules/*.md": "Roo Code rules",
    ".kilocode/rules/*.md": "Kilo Code rules",
    ".junie/guidelines.md": "Junie",
    "CONVENTIONS.md": "Aider (when listed under read:)",
}
# Tool folders where a stray .md at the top level is probably read by nothing.
TOOL_FOLDERS = [".cursor", ".windsurf", ".cline", ".roo", ".kilocode", ".copilot",
                ".agent", ".agents", ".antigravity", ".vscode", ".junie", ".gemini"]
POINTER_MAX_BYTES = 1500
CANONICAL = "AGENTS.md"


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def classify(path: Path, canonical_text: str | None) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if canonical_text is not None and normalize(text) == normalize(canonical_text):
        return "copy"
    if re.search(r"^\s*@\.?/?AGENTS\.md\s*$", text, re.M):
        return "import"
    if len(text.encode("utf-8")) <= POINTER_MAX_BYTES and re.search(r"AGENTS\.md|CLAUDE\.md", text):
        return "pointer"
    return "diverged" if canonical_text is not None else "standalone"


def find_known(root: Path) -> list[tuple[Path, str]]:
    found = []
    for pattern, tool in KNOWN_FILES.items():
        for path in sorted(root.glob(pattern)):
            if path.is_file():
                found.append((path, tool))
    return found


def find_orphans(root: Path, known: set[Path]) -> list[Path]:
    orphans = []
    for folder in TOOL_FOLDERS:
        base = root / folder
        if base.is_dir():
            for path in sorted(base.glob("*.md")):
                if path.is_file() and path not in known:
                    orphans.append(path)
    github = root / ".github"
    if github.is_dir():
        for path in sorted(github.glob("*.md")):
            if path.name.lower() not in {"copilot-instructions.md", "pull_request_template.md",
                                         "contributing.md", "security.md", "code_of_conduct.md",
                                         "funding.md", "support.md"} and path not in known:
                orphans.append(path)
    return orphans


def gemini_setting(root: Path) -> str | None:
    settings = root / ".gemini" / "settings.json"
    if not settings.is_file():
        return None
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return "unreadable .gemini/settings.json"
    names = (data.get("context") or {}).get("fileName")
    return f".gemini/settings.json context.fileName = {names!r}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("repo", nargs="?", default=".", type=Path)
    parser.add_argument("--strict", action="store_true", help="exit 1 when problems are found")
    args = parser.parse_args()

    root = args.repo.resolve()
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        return 2

    canonical_path = root / CANONICAL
    canonical_text = canonical_path.read_text(encoding="utf-8", errors="replace") if canonical_path.is_file() else None
    known = find_known(root)
    known_paths = {path for path, _ in known}
    problems = 0

    print(f"Repository: {root}")
    if canonical_text is None:
        print("  No AGENTS.md at the root. Pick one canonical file first.")
        problems += 1

    print("\nInstruction files that tools load:")
    for path, tool in known:
        rel = path.relative_to(root).as_posix()
        if path == canonical_path:
            kind = "canonical"
        else:
            kind = classify(path, canonical_text)
        size = path.stat().st_size
        print(f"  {kind:<10} {rel:<45} {size:>7} B  {tool}")
        if kind in {"copy", "diverged"}:
            problems += 1

    orphans = find_orphans(root, known_paths)
    if orphans:
        print("\nMarkdown in tool folders at paths no known tool reads (probably ignored):")
        for path in orphans:
            print(f"  orphan     {path.relative_to(root).as_posix()}")
        problems += len(orphans)

    setting = gemini_setting(root)
    if setting:
        print(f"\n{setting}")

    print("\nKinds: canonical = AGENTS.md; import = loads it with @AGENTS.md; pointer = short file that "
          "points to it; copy = full duplicate (will drift); diverged = different content (already drifted).")
    print(f"\n{problems} problem(s) found.")
    return 1 if args.strict and problems else 0


if __name__ == "__main__":
    sys.exit(main())
