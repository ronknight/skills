"""Report what a spreadsheet file really is, whatever its extension says. Read-only.

Usage: python sniff_spreadsheet.py FILE [FILE ...]

Detects legacy BIFF .xls (OLE2), encrypted OOXML, .xlsx/.xlsm (ZIP), XML
Spreadsheet 2003, HTML tables, and delimited text, and names a reader for each.
Many "Excel" exports from ERP and reporting systems are HTML or tab-delimited
text with an .xls extension, and many ".xls" files written by pandas/openpyxl
are really .xlsx. Standard library only; reads the first bytes and the ZIP
directory, writes nothing.
"""
from __future__ import annotations

import csv
import sys
import zipfile
from pathlib import Path

OLE2_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")
ZIP_MAGIC = b"PK\x03\x04"


def utf16(name: str) -> bytes:
    return name.encode("utf-16-le")


def ole2_streams(path: Path, names: list[str]) -> set[str]:
    """Find directory-entry names anywhere in an OLE2 file (the directory can sit at the end)."""
    wanted = {name: utf16(name) for name in names}
    overlap = max(len(v) for v in wanted.values())
    found: set[str] = set()
    tail = b""
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1 << 20)
            if not chunk:
                return found
            block = tail + chunk
            found.update(name for name, raw in wanted.items() if raw in block)
            tail = block[-overlap:]


def sniff(path: Path) -> tuple[str, str]:
    with path.open("rb") as fh:
        head = fh.read(65536)
    if head.startswith(OLE2_MAGIC):
        streams = ole2_streams(path, ["EncryptedPackage", "Workbook", "Book", "WordDocument"])
        if "EncryptedPackage" in streams:
            return "encrypted OOXML (password-protected .xlsx)", "decrypt first (e.g. msoffcrypto-tool), then openpyxl"
        if "Workbook" in streams:
            return "BIFF8 .xls (Excel 97-2003)", "xlrd (read); xlwt or xlutils (write)"
        if "Book" in streams:
            return "BIFF5 .xls (Excel 5/95)", "xlrd (read); convert before editing"
        if "WordDocument" in streams:
            return "Word document (OLE2), not a workbook", "check the source"
        return "OLE2 container, not obviously a workbook", "check the source"
    if head.startswith(ZIP_MAGIC):
        try:
            names = set(zipfile.ZipFile(path).namelist())
        except zipfile.BadZipFile:
            return "damaged ZIP", "re-export the file"
        if "xl/workbook.xml" in names:
            kind = ".xlsm (macro-enabled OOXML)" if "xl/vbaProject.bin" in names else ".xlsx (OOXML)"
            return kind, "openpyxl (pass a BytesIO if the extension is .xls)"
        if "content.xml" in names and "mimetype" in names:
            return "OpenDocument spreadsheet (.ods)", "pandas read_excel(engine='odf') or LibreOffice"
        return "ZIP archive, not a workbook", "check the source"
    text = head.lstrip(b"\xef\xbb\xbf").lstrip()
    if head.startswith((b"\xff\xfe", b"\xfe\xff")):
        return "UTF-16 text (likely tab-delimited 'Unicode text' export)", "open with encoding='utf-16', delimiter='\\t'"
    lowered = text[:4096].lower()
    if lowered.startswith(b"<?xml") and b"urn:schemas-microsoft-com:office:spreadsheet" in lowered:
        return "XML Spreadsheet 2003", "parse as XML, or convert with LibreOffice"
    if lowered.startswith((b"<html", b"<!doctype", b"<table", b"<meta")) or b"<table" in lowered:
        return "HTML table saved with a spreadsheet extension", "pandas.read_html, or an HTML parser"
    try:
        sample = text[:8192].decode("utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError:
        sample = text[:8192].decode("cp1252", errors="replace")
        encoding = "cp1252 (guess)"
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters="\t,;|")
        delimiter = {"\t": "tab"}.get(dialect.delimiter, repr(dialect.delimiter))
        return f"delimited text ({delimiter}, {encoding})", "csv module with that delimiter and encoding"
    except csv.Error:
        return f"unrecognised text ({encoding})", "inspect by hand"


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__.strip())
        return 2
    status = 0
    for name in argv:
        path = Path(name)
        if not path.is_file():
            print(f"{name}: not a file")
            status = 1
            continue
        kind, reader = sniff(path)
        ext = path.suffix.lower()
        mismatch = ""
        if ext == ".xls" and not kind.startswith(("BIFF8", "BIFF5")):
            mismatch = "  <- extension says .xls"
        elif ext in (".xlsx", ".xlsm") and not kind.startswith((".xlsx", ".xlsm")):
            mismatch = f"  <- extension says {ext}"
        print(f"{name}: {kind}{mismatch}\n    reader: {reader}")
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
