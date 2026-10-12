"""List every request in a Postman collection (v2.0/v2.1) as an audit inventory.

Usage:
    python postman_inventory.py COLLECTION.json          # markdown table
    python postman_inventory.py COLLECTION.json --csv    # CSV

Also warns on stderr when the collection contains literal credentials, which
means it must not be committed or shared. Warnings name where a credential is,
never its value. Standard library only; reads the file and makes no network calls.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterator

SECRET_NAME = re.compile(
    r"passw(or)?d|passphrase|^pass$|secret|token|api[-_]?key|(^|[-_])auth(orization)?$"
    r"|cookie|session|bearer|credential|private[-_]?key",
    re.I,
)
TEMPLATE_ONLY = re.compile(r"^\s*\{\{[^}]+\}\}\s*$")
URL_PASSWORD = re.compile(r"^\s*[a-z][a-z0-9+.-]*://[^/@\s:]*:([^/@\s]+)@", re.I)
RAW_JSON_FIELD = re.compile(r'"([^"\\]+)"\s*:\s*"([^"\\]*)"')
# In an apikey auth block, "key" is the header name and "value" is the secret.
AUTH_SECRET_KEYS = {"token", "password", "value", "secret", "accessToken", "clientSecret"}
# Spreadsheet apps run a cell that starts with one of these as a formula.
FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def is_literal_secret(name: str | None, value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    return bool(SECRET_NAME.search(name or "")) and not TEMPLATE_ONLY.match(value)


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


def url_secrets(url: Any, where: str) -> list[str]:
    found = []
    raw = url if isinstance(url, str) else (url or {}).get("raw", "")
    password = URL_PASSWORD.match(raw)
    if password and not TEMPLATE_ONLY.match(password.group(1)):
        found.append(f"{where}: password in URL")
    # Disabled parameters still sit in the file, so check them too.
    if isinstance(url, dict) and url.get("query"):
        pairs = [(q.get("key"), q.get("value")) for q in url["query"] if isinstance(q, dict)]
    else:
        pairs = re.findall(r"[?&]([^=&#]+)=([^&#]*)", raw)
    for key, value in pairs:
        if is_literal_secret(key, value):
            found.append(f"{where}: literal value in query parameter '{key}'")
    return found


def body_secrets(body: dict, where: str) -> list[str]:
    mode = body.get("mode", "")
    if mode in ("urlencoded", "formdata"):
        pairs = [(f.get("key"), f.get("value")) for f in body.get(mode) or [] if isinstance(f, dict)]
    elif mode == "raw":
        pairs = RAW_JSON_FIELD.findall(body.get("raw") or "")
    else:
        pairs = []
    return [f"{where}: literal value in body field '{key}'"
            for key, value in pairs if is_literal_secret(key, value)]


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
        name = " ".join(" / ".join(folder + (item.get("name", ""),)).split())
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
        warnings += url_secrets(req.get("url"), name)
        warnings += body_secrets(body, name)
        for header in req.get("header", []) or []:
            if isinstance(header, dict) and is_literal_secret(header.get("key", ""), header.get("value")):
                warnings.append(f"{name}: literal value in header '{header.get('key')}'")
    return rows, warnings


def md_cell(value: str) -> str:
    return " ".join(value.split()).replace("|", "\\|")


def csv_cell(value: str) -> str:
    return "'" + value if value.startswith(FORMULA_START) else value


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
        writer.writerows({f: csv_cell(row[f]) for f in fields} for row in rows)
    else:
        print("| " + " | ".join(fields) + " |")
        print("|" + "---|" * len(fields))
        for row in rows:
            print("| " + " | ".join(md_cell(row[f]) for f in fields) + " |")

    print(f"{len(rows)} requests", file=sys.stderr)
    if warnings:
        print(f"WARNING: {len(warnings)} literal credential(s) found. Don't commit or share this collection:", file=sys.stderr)
        for message in warnings:
            print(f"  - {message}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
