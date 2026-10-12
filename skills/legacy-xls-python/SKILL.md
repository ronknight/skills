---
name: legacy-xls-python
description: Read, write and convert legacy Excel 97-2003 .xls files from Python without breaking the systems that consume them - detect what a "spreadsheet" really is (true BIFF .xls, .xlsx in disguise, HTML table, tab-delimited text), pick the right library (xlrd, xlwt, xlutils, openpyxl, LibreOffice), copy an import template while keeping its styles, respect .xls limits, and export clean UTF-8 tab-delimited text. Use when an importer or ERP requires .xls, when Excel warns "the file format and extension don't match", when pandas or openpyxl can't open a file, or when converting between .xls, .xlsx and CSV.
license: MIT
---

# Legacy .xls in Python

Old import screens, ERPs and reporting tools still require, or produce, Excel
97-2003 `.xls` files. Python's libraries split the format awkwardly, and many
files named `.xls` aren't `.xls` at all.

## 1. Find out what the file really is

```bash
python scripts/sniff_spreadsheet.py export.xls other.xlsx
```

It reads the file's bytes, not its extension, and names a reader. It's
read-only and uses only the standard library. Common findings:

| Really is | Typical source | Read with |
|---|---|---|
| BIFF8 `.xls` | Excel, true legacy exports | `xlrd` |
| `.xlsx` named `.xls` | pandas or openpyxl writing to a `.xls` filename | `openpyxl` via `BytesIO` |
| HTML table named `.xls` | web reports, ERP "export to Excel" | `pandas.read_html` |
| tab-delimited text named `.xls` | ERP and report-writer exports | `csv`, with the right encoding |
| UTF-16 text | Excel "Unicode Text" | `encoding="utf-16"`, tab delimiter |
| encrypted OLE2 | password-protected `.xlsx` | decrypt first |

## 2. Pick the library

| Task | Library | Notes |
|---|---|---|
| Read `.xls` | `xlrd` 2.x | reads `.xls` only (2.0 dropped `.xlsx`) |
| Write a new `.xls` | `xlwt` | write-only; can't open existing files |
| Edit or copy an existing `.xls` keeping styles | `xlrd` (`formatting_info=True`) + `xlutils` | see section 4 |
| Read or write `.xlsx` | `openpyxl` | can't read `.xls` at all |
| pandas to `.xls` | not possible | pandas 2.0 removed the `xlwt` engine; write with `xlwt` directly |
| Convert anything | LibreOffice headless | `soffice --headless --convert-to xls:"MS Excel 97" --outdir out in.xlsx` |
| Edit in place, keep everything | Excel COM on Windows | see the `excel-com-safe-write` skill |

## 3. The disguised-.xlsx trap

`df.to_excel("out.xls")` with openpyxl, or `Workbook().save("out.xls")`, writes
**.xlsx content with a .xls name**. Excel opens it with a "format and extension
don't match" warning, and strict importers reject it. If the consumer needs
real `.xls`, write it with `xlwt`, or convert with LibreOffice, then run the
sniffer to confirm it's BIFF8.

openpyxl also refuses files by extension. To read xlsx content that has a `.xls`
name, hand it the bytes:

```python
import io
from openpyxl import load_workbook

with open(path, "rb") as fh:
    wb = load_workbook(io.BytesIO(fh.read()), read_only=True, data_only=True)
```

## 4. Copy an import template, keep its styles

Import screens are picky about headers, cell types and sometimes styles. Copy
the template rather than rebuilding it:

```python
import xlrd
from xlutils.filter import XLWTWriter

template = xlrd.open_workbook("template.xls", formatting_info=True)
sheet = template.sheet_by_index(0)
writer = XLWTWriter()
writer.start()
writer.workbook(template, "out.xls")
writer.sheet(sheet, sheet.name)
for r in range(sheet.nrows):
    writer.row(r, r)
    for c in range(sheet.ncols):
        writer.cell(r, c, r, c)                       # copies value and style
style = writer.style_list[sheet.cell_xf_index(1, 3)]  # template's style for row 1, col 3
writer.wtsheet.write(1, 3, "new value", style)        # write with the template's style
writer.finish()
writer.output[0][1].save("out.xls")
```

- `formatting_info=True` is required or styles are lost.
- Write new values with the template cell's own style (`style_list[...]`), not
  a fresh `easyxf`.
- Then **re-read the output** with xlrd and compare headers, values, cell types
  and dimensions to what you intended.

## 5. Limits of .xls

- 65,536 rows and 256 columns per sheet; xlwt raises past them. Split the
  data, or the consumer has to accept `.xlsx`.
- Sheet names: 31 characters, no `[]:*?/\`.
- Cell text: 32,767 characters, no control characters.
- Styles: about 4,000 unique formats per workbook. Creating a new `easyxf`
  per cell hits the limit; create each style once and reuse it.

## 6. Values coming back wrong

- **Numbers are floats.** An ID `12345` reads as `12345.0`, and `00123` was
  probably stored as `123` already. If a column holds codes, convert with
  `str(int(v))` only after checking that it's integral, and fix leading zeros
  at the source (store it as text).
- **Dates are serial numbers.** Convert with
  `xlrd.xldate_as_datetime(value, book.datemode)`. The workbook's date mode
  (1900 or 1904) matters.
- **Empty cells** come back as `""` with type `XL_CELL_EMPTY`; check the type,
  not the value.
- Merged cells hold their value only in the top-left cell.

## 7. Export clean tab-delimited text

For systems that import text:

- Write UTF-8; add a BOM (`encoding="utf-8-sig"`) only if people will open it in
  Excel, because some importers choke on a BOM.
- Replace tabs and newlines inside values (HTML descriptions often contain
  both), or the row breaks.
- Strip only matched wrapping quotes (`"value"` becomes `value`); never strip
  quotes that belong to the content, such as inch marks.
- Quote with `csv.writer(..., delimiter="\t", quoting=csv.QUOTE_MINIMAL)`
  rather than joining strings yourself.

## 8. Safety

- Never write over the source file. Write to a new path, verify, then let the
  user replace the original.
- Values that start with `=`, `+`, `-` or `@` are treated as formulas when
  opened in Excel. If the data came from users or the web, prefix such text
  values with `'` or a space before writing.
- Workbooks from outside can carry macros. Read them with these libraries
  (which don't run macros) rather than opening them in Excel from a script.
