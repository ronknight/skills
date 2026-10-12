---
name: excel-com-safe-write
description: Write to Excel workbooks through COM automation (PowerShell or Python pywin32) without silently losing changes - refuse while the workbook or Excel is open, back up first, catch read-only opens, release COM objects, and verify by reading the saved file back. Use when editing .xls/.xlsx/.xlsm through Excel.Application on Windows, especially legacy .xls files that openpyxl can't open, or when an Excel automation reported success but the changes are missing.
license: MIT
---

# Safe Excel COM writes

## The failure this prevents

A COM script sets the cells, `Save()` returns cleanly, the script prints
"done", and the change is gone. The usual cause is that someone had the
workbook open in Excel. Their session still holds the old contents and saves
over yours the next time they (or AutoRecover) save. Nothing raises an error.
Only reading the saved file back shows it.

Related traps that are just as quiet:

- The file was locked, so Excel opened it **read-only**, and the save never
  reached the original file.
- `GetActiveObject` (PowerShell/.NET) or `win32com.client.Dispatch` (Python)
  attached to the user's own running Excel, so you edited their in-memory copy.
- Leaked COM references left a headless `EXCEL.EXE` running that keeps the
  file locked for the next run.

## Rules

1. **Guard before writing.** Stop if:
   - any Excel process is running. Ask the user to close Excel; don't kill it,
     because it may hold unsaved work. Excel processes with no window are
     usually leftovers from earlier automation. List them and ask before
     stopping them.
   - an owner file `~$<workbook name>` sits next to the workbook. Excel creates
     it while the file is open, including on another machine over a share. If
     Excel isn't running anywhere, it's a stale lock from a crash.
   - the file can't be opened for exclusive access. Something else holds it.
2. **Back up first.** Copy the workbook to a timestamped file before writing.
   If the folder is git-ignored, that copy is the only way back.
3. **Use your own instance.** `New-Object -ComObject Excel.Application` in
   PowerShell, `win32com.client.DispatchEx("Excel.Application")` in Python.
   Never attach to a running instance.
4. **Open with macros off.** A COM-started Excel runs workbook macros by
   default. Set `AutomationSecurity = 3` (force-disable) before
   `Workbooks.Open`, and pass `UpdateLinks = 0` so external links aren't
   fetched. Treat `.xls` and `.xlsm` from anyone else as untrusted.
5. **Check `ReadOnly` after opening.** If it's true, close without saving and
   stop.
6. **Write values, not formulas.** Excel stores text that starts with `=`, `+`,
   `-` or `@` as a formula, and a formula can reach the network (`WEBSERVICE`)
   or other programs (DDE). Refuse such strings unless the user asked for that
   formula, and pass numbers as numbers.
7. **Keep the format.** `Save()` keeps the original format. If you need
   `SaveAs`, pass `FileFormat` explicitly (56 = `.xls`, 51 = `.xlsx`,
   52 = `.xlsm`). Otherwise the bytes may not match the extension.
8. **Clean up in `finally`.** `Close($false)`, `Quit()`, then
   `ReleaseComObject` on the workbook and application and run the garbage
   collector. In Python, drop the references and call `pythoncom.CoUninitialize()`
   in threads where you called `CoInitialize()`.
9. **Verify from a fresh process.** Re-read every cell you wrote, from a new
   read-only Excel instance or an independent reader library, and compare. Don't
   trust the script's own success message.

## Library notes

- **`.xls` (BIFF)**: `xlrd` 2.x reads it but can't write. `openpyxl` can't open
  it. `xlwt` only creates new files. For in-place edits, Excel COM is the
  practical path, and `xlrd` makes a good independent verifier.
- **`.xlsx`/`.xlsm`**: `openpyxl` avoids COM entirely, but it drops content it
  doesn't model (shapes, some charts and images) when it re-saves an existing
  file. The "someone has it open" guard still applies: their save still wins.
- **Comparing values**: Excel coerces input. `"00123"` becomes the number 123,
  and long digit strings lose precision. Dates come back as serial numbers
  through `Value2`. Compare by type: exact for strings, a small tolerance for
  numbers, `ToOADate()` for dates.

## Script

[scripts/Set-ExcelCells.ps1](scripts/Set-ExcelCells.ps1) applies all of the
above to single-cell edits:

```powershell
.\scripts\Set-ExcelCells.ps1 -Path .\prices.xls -Sheet Sheet1 -Values @{ B2 = 19.99; C2 = 'Discontinued' }
```

When calling from another shell with `powershell -File`, pass `-Values` as a
JSON object instead: `'{"B2": 19.99, "C2": "Discontinued"}'`.

It refuses text values that would become formulas. If a guard trips, it exits 1
without touching the file. It prints the backup
path once the backup exists, and exits 1 with the mismatching cells if
verification fails.
