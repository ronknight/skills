"""List every request in a Postman collection (v2.0/v2.1) as an audit inventory.

Usage:
    python postman_inventory.py COLLECTION.json          # markdown table
    python postman_inventory.py COLLECTION.json --csv    # CSV

Also warns on stderr when the collection contains literal credentials, which
means it must not be committed or shared. Standard library only.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterator

SECRET_NAME = re.compile(r"pass(word)?|secret|token|api[-_]?key|auth|cookie|session|bearer", re.I)
TEMPLATE_ONLY = re.compile(r"^\s*\{\{[^}]+\}\}\s*$")
# In an apikey auth block, "key" is the header name and "value" is the secret.
AUTH_SECRET_KEYS = {"token", "password", "value", "secret", "accessToken", "clientSecret"}


def is_literal_secret(name: str, value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    return bool(SECRET_NAME.search(name)) and not TEMPLATE_ONLY.match(value)


def walk(items: list[dict], folder: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], dict]]:
    for item in items:
        if "item" in item:
            yield from walk(item["item"], folder + (item.get("name", ""),))
        elif "request" in item:
            yield folder, item


def url_parts(url: Any) -> tuple[str, list[str]]:
    if isinstance(url, str):
        raw = url
        query = re.findall(r"[?&]([^=&#]+)", raw)
    else:
        url = url or {}
        raw = url.get("raw", "")
        query = [q.get("key", "") for q in url.get("query", []) if not q.get("disabled")]
    path = re.sub(r"^\s*(\{\{[^}]+\}\}|https?://[^/]+)", "", raw.split("?")[0]) or "/"
    return path, query


def auth_secrets(auth: dict | None, where: str) -> list[str]:
    found = []
    if not auth:
        return found
    kind = auth.get("type", "")
    entries = auth.get(kind, [])
    if isinstance(entries, dict):  # v2.0 stores auth fields as an object
        entries = [{"key": k, "value": v} for k, v in entries.items()]
    for entry in entries:
        key, value = entry.get("key", ""), entry.get("value")
        if (key in AUTH_SECRET_KEYS and isinstance(value, str) and value.strip()
                and not TEMPLATE_ONLY.match(value)):
            found.append(f"{where}: literal {kind} auth '{key}'")
    return found


def scan(collection: dict) -> tuple[list[dict], list[str]]:
    rows, warnings = [], []
    warnings += auth_secrets(collection.get("auth"), "collection")
    for var in collection.get("variable", []):
        if is_literal_secret(var.get("key", ""), var.get("value")):
            warnings.append(f"collection variable '{var.get('key')}' has a literal value")

    for folder, item in walk(collection.get("item", [])):
        req = item["request"]
        if isinstance(req, str):  # bare URL shorthand
            req = {"method": "GET", "url": req}
        name = " / ".join(folder + (item.get("name", ""),))
        path, query = url_parts(req.get("url"))
        body = req.get("body") or {}
        rows.append({
            "folder": " / ".join(folder),
            "name": item.get("name", ""),
            "method": req.get("method", "GET").upper(),
            "path": path,
            "query": ", ".join(query),
            "body": body.get("mode", ""),
            "status": "untested",
        })
        warnings += auth_secrets(req.get("auth"), name)
        for header in req.get("header", []) or []:
            if isinstance(header, dict) and is_literal_secret(header.get("key", ""), header.get("value")):
                warnings.append(f"{name}: literal value in header '{header.get('key')}'")
    return rows, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("collection", type=Path)
    parser.add_argument("--csv", action="store_true", help="write CSV instead of a markdown table")
    args = parser.parse_args()

    collection = json.loads(args.collection.read_text(encoding="utf-8"))
    rows, warnings = scan(collection)
    fields = ["folder", "name", "method", "path", "query", "body", "status"]

    if args.csv:
        writer = csv.DictWriter(sys.stdout, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    else:
        print("| " + " | ".join(fields) + " |")
        print("|" + "---|" * len(fields))
        for row in rows:
            print("| " + " | ".join(row[f].replace("|", "\\|") for f in fields) + " |")

    print(f"{len(rows)} requests", file=sys.stderr)
    if warnings:
        print(f"WARNING: {len(warnings)} literal credential(s) found. Don't commit or share this collection:", file=sys.stderr)
        for message in warnings:
            print(f"  - {message}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
