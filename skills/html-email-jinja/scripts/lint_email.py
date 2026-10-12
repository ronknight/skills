"""Lint rendered HTML email files for problems that break in real inboxes.

Usage: python lint_email.py FILE [FILE ...]
Exits 1 if any file has errors. Standard library only.
"""
from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

GMAIL_CLIP_BYTES = 102 * 1024
LEFTOVER_TEMPLATE = re.compile(r"\{\{.*?\}\}|\{%.*?%\}")
IGNORED_HREF_SCHEMES = ("mailto:", "tel:", "sms:", "#")


class EmailLinter(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.has_color_scheme = False

    def _where(self) -> str:
        return f"line {self.getpos()[0]}"

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {name: (value or "") for name, value in attrs}
        if tag == "img":
            src = a.get("src", "")
            if not src.startswith("https://"):
                self.errors.append(f"{self._where()}: <img> src is not absolute https: {src!r}")
            if "alt" not in a:
                self.errors.append(f"{self._where()}: <img> has no alt attribute: {src!r}")
            if not a.get("width"):
                self.warnings.append(f"{self._where()}: <img> has no width attribute: {src!r}")
        elif tag == "a":
            href = a.get("href", "").strip()
            if not href:
                self.errors.append(f"{self._where()}: <a> has an empty href")
            elif href.startswith(IGNORED_HREF_SCHEMES):
                pass
            elif href.startswith("http://"):
                self.warnings.append(f"{self._where()}: <a> uses http, not https: {href!r}")
            elif not href.startswith("https://") and "|" not in href:
                # Values like *|UNSUB|* are ESP merge tags, filled in at send time.
                self.errors.append(f"{self._where()}: <a> href is not absolute: {href!r}")
        elif tag in ("script", "form", "iframe"):
            self.errors.append(f"{self._where()}: <{tag}> is stripped or blocked by most email clients")
        elif tag == "meta" and a.get("name", "").lower() == "color-scheme":
            self.has_color_scheme = True


def lint(path: Path) -> tuple[list[str], list[str]]:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    linter = EmailLinter()
    linter.feed(text)
    linter.close()
    errors, warnings = linter.errors, linter.warnings

    if not text.lstrip().lower().startswith("<!doctype"):
        errors.append("missing doctype; clients fall back to quirks rendering")
    if not linter.has_color_scheme:
        warnings.append('missing <meta name="color-scheme">; dark mode may invert colours unpredictably')
    for match in LEFTOVER_TEMPLATE.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        warnings.append(f"line {line}: template syntax left in output (fine only if it is an ESP tag): {match.group(0)[:60]!r}")
    if len(raw) > GMAIL_CLIP_BYTES:
        errors.append(f"{len(raw) // 1024} KB is over Gmail's ~102 KB clipping limit")
    return errors, warnings


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip())
        return 2
    failed = False
    for name in argv:
        path = Path(name)
        errors, warnings = lint(path)
        status = "FAIL" if errors else "ok"
        print(f"{status}  {path}  ({len(errors)} errors, {len(warnings)} warnings)")
        for message in errors:
            print(f"  error    {message}")
        for message in warnings:
            print(f"  warning  {message}")
        failed = failed or bool(errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
