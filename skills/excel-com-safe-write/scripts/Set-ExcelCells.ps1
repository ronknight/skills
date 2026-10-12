<#
.SYNOPSIS
Write single-cell values to an Excel workbook through COM, then verify them by
reading the saved file back in a fresh Excel instance.

.DESCRIPTION
Refuses to run while Excel is running, while an owner (~$) file exists, or while
the workbook is locked. Backs the workbook up, writes in a private Excel
instance, refuses read-only opens, and re-reads every written cell afterwards.
Exits 1 on any guard failure or verification mismatch.

.EXAMPLE
.\Set-ExcelCells.ps1 -Path .\prices.xls -Sheet Sheet1 -Values @{ B2 = 19.99; C2 = 'Discontinued' }

.EXAMPLE
# From another shell, where a hashtable can't be passed, use a JSON object:
powershell -File Set-ExcelCells.ps1 -Path prices.xls -Sheet Sheet1 -Values '{"B2": 19.99, "C2": "Discontinued"}'
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string]$Path,
    [Parameter(Mandatory = $true)] [string]$Sheet,
    [Parameter(Mandatory = $true)] [object]$Values,
    [string]$BackupDir
)
$ErrorActionPreference = 'Stop'

if ($Values -is [string]) {
    $parsed = $Values | ConvertFrom-Json
    $Values = @{}
    foreach ($property in $parsed.PSObject.Properties) {
        $value = $property.Value
        if ($value -is [decimal]) { $value = [double]$value }
        $Values[$property.Name] = $value
    }
}
if ($Values -isnot [hashtable]) { throw '-Values must be a hashtable or a JSON object string.' }

$Path = (Resolve-Path -LiteralPath $Path).Path
foreach ($cell in $Values.Keys) {
    if ($cell -notmatch '^[A-Za-z]{1,3}[0-9]+$') { throw "Not a single-cell address: '$cell'" }
}

function Assert-WorkbookFree([string]$File) {
    $running = @(Get-Process -Name EXCEL -ErrorAction SilentlyContinue)
    if ($running.Count -gt 0) {
        $headless = @($running | Where-Object { $_.MainWindowHandle -eq 0 }).Count
        throw "Excel is running ($($running.Count) process(es), $headless without a window). Close Excel and retry. Windowless ones are usually leftovers from earlier automation; check before stopping them."
    }
    $owner = Join-Path (Split-Path -Parent $File) ('~$' + (Split-Path -Leaf $File))
    if (Test-Path -LiteralPath $owner) {
        throw "Owner file exists: $owner. The workbook is open somewhere, or that is a stale lock from a crash."
    }
    try {
        $stream = [System.IO.File]::Open($File, 'Open', 'ReadWrite', 'None')
        $stream.Close()
    } catch [System.IO.IOException] {
        throw "Workbook is locked by another process: $File"
    }
}

function Invoke-WithWorkbook([string]$File, [bool]$ReadOnly, [scriptblock]$Action) {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $wb = $null
    try {
        $wb = $excel.Workbooks.Open($File, 0, $ReadOnly)
        & $Action $wb
    } finally {
        if ($wb) {
            $wb.Close($false)
            [void][Runtime.InteropServices.Marshal]::ReleaseComObject($wb)
        }
        $excel.Quit()
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)
        [GC]::Collect()
        [GC]::WaitForPendingFinalizers()
    }
}

function Test-SameValue($Expected, $Actual) {
    if ($null -eq $Expected -or ($Expected -is [string] -and $Expected -eq '')) {
        return ($null -eq $Actual -or ($Actual -is [string] -and $Actual -eq ''))
    }
    if ($Expected -is [string]) { return ($Actual -is [string] -and $Actual -ceq $Expected) }
    if ($Expected -is [bool]) { return ($Actual -is [bool] -and $Actual -eq $Expected) }
    if ($Expected -is [datetime]) { $Expected = $Expected.ToOADate() }
    if ($null -eq $Actual -or $Actual -is [string]) { return $false }
    $e = [double]$Expected
    $a = [double]$Actual
    return ([math]::Abs($e - $a) -le 1e-9 * [math]::Max(1.0, [math]::Abs($e)))
}

Assert-WorkbookFree $Path

if (-not $BackupDir) { $BackupDir = Split-Path -Parent $Path }
New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
$backup = Join-Path $BackupDir ((Split-Path -Leaf $Path) + '.' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '.bak')
Copy-Item -LiteralPath $Path -Destination $backup
Write-Host "Backup: $backup"

Invoke-WithWorkbook $Path $false {
    param($wb)
    if ($wb.ReadOnly) { throw 'Excel opened the workbook read-only; nothing was written.' }
    $ws = $wb.Worksheets.Item($Sheet)
    foreach ($cell in $Values.Keys) {
        $ws.Range($cell).Value2 = $Values[$cell]
    }
    $wb.Save()
}

$mismatches = New-Object System.Collections.Generic.List[string]
Invoke-WithWorkbook $Path $true {
    param($wb)
    $ws = $wb.Worksheets.Item($Sheet)
    foreach ($cell in $Values.Keys) {
        $actual = $ws.Range($cell).Value2
        if (-not (Test-SameValue $Values[$cell] $actual)) {
            $mismatches.Add("$cell expected '$($Values[$cell])' but the saved file has '$actual'")
        }
    }
}

if ($mismatches.Count -gt 0) {
    $mismatches | ForEach-Object { Write-Error $_ -ErrorAction Continue }
    Write-Host "Verification failed. Restore from: $backup"
    exit 1
}
Write-Host "Verified $($Values.Count) cell(s) in $Path"
exit 0
