"""Show the skills.sh security audit results for every skill in this repo.

Usage:
    python scripts/check_audits.py [OWNER/REPO] [--strict]

OWNER/REPO defaults to the GitHub origin remote. Exits 1 if any audit is "fail",
or "warn" as well with --strict. skills.sh audits a skill a few minutes after its
first install with the skills CLI (telemetry on). Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://skills.sh/api/v1/skills/audit/{source}/{slug}"
ROOT = Path(__file__).resolve().parent.parent
SUMMARY_WIDTH = 100


def origin_repo() -> str:
    url = subprocess.run(["git", "-C", str(ROOT), "remote", "get-url", "origin"],
                         capture_output=True, text=True, check=True).stdout.strip()
    match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?/?$", url)
    if not match:
        sys.exit(f"origin is not a GitHub URL ({url}); pass OWNER/REPO")
    return match.group(1)


def skill_slugs() -> list[str]:
    slugs = []
    for skill_md in sorted(ROOT.glob("skills/*/SKILL.md")):
        match = re.search(r"^name:\s*(\S+)", skill_md.read_text(encoding="utf-8"), re.M)
        slugs.append(match.group(1) if match else skill_md.parent.name)
    return slugs


def fetch_audits(source: str, slug: str) -> list[dict] | None:
    """Return the audit entries, or None if skills.sh hasn't audited the skill yet."""
    request = urllib.request.Request(
        API.format(source=source, slug=slug),
        headers={"Accept": "application/json", "User-Agent": "check_audits.py"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response).get("audits", [])
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("repo", nargs="?", help="OWNER/REPO (default: the origin remote)")
    parser.add_argument("--strict", action="store_true", help="exit 1 on warn as well as fail")
    args = parser.parse_args()
    sys.stdout.reconfigure(errors="replace")

    source = args.repo or origin_repo()
    failing = {"fail", "warn"} if args.strict else {"fail"}
    bad = False
    for slug in skill_slugs():
        audits = fetch_audits(source, slug)
        if audits is None:
            print(f"{slug}: not audited yet (install it once with the skills CLI, telemetry on)")
            continue
        print(f"{slug}:")
        for audit in audits:
            status = audit.get("status", "?")
            summary = " ".join(audit.get("summary", "").split())
            if len(summary) > SUMMARY_WIDTH:
                summary = summary[:SUMMARY_WIDTH - 3] + "..."
            print(f"  {status:<5} {audit.get('provider', '?'):<20} {audit.get('riskLevel') or '-':<8} {summary}")
            if status != "pass":
                print(f"        https://skills.sh/{source}/{slug}/security/{audit.get('slug', '')}")
            bad = bad or status in failing
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
