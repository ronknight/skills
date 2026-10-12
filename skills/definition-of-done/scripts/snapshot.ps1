<#
.SYNOPSIS
Copy a project into archive\<yyyy-MM-dd_HHmmss>\ as a local restore point.

.EXAMPLE
.\snapshot.ps1
.\snapshot.ps1 -ProjectPath ..\my-app
#>
param(
    [string]$ProjectPath = (Get-Location).Path,
    [string]$ArchivePath
)
$ErrorActionPreference = 'Stop'

$ProjectPath = (Resolve-Path -LiteralPath $ProjectPath).Path
if (-not $ArchivePath) { $ArchivePath = Join-Path $ProjectPath 'archive' }
New-Item -ItemType Directory -Path $ArchivePath -Force | Out-Null
$ArchivePath = (Resolve-Path -LiteralPath $ArchivePath).Path

$Dest = Join-Path $ArchivePath (Get-Date -Format 'yyyy-MM-dd_HHmmss')
if (Test-Path -LiteralPath $Dest) { throw "Snapshot already exists: $Dest" }
New-Item -ItemType Directory -Path $Dest | Out-Null

# robocopy /XD: bare names match at any depth, full paths match that folder only.
$AnyDepth = @('.git', '.venv', 'venv', '__pycache__', 'node_modules', '.pytest_cache', '.mypy_cache', '.ruff_cache')
$TopLevel = @('build', 'dist', 'target') | ForEach-Object { Join-Path $ProjectPath $_ }
$ExcludeDirs = $AnyDepth + $TopLevel + $ArchivePath

robocopy $ProjectPath $Dest /E /XD $ExcludeDirs /XF '*.pyc' '.DS_Store' /R:1 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy failed with exit code $LASTEXITCODE" }

if (Get-Command git -ErrorAction SilentlyContinue) {
    git -C $ProjectPath rev-parse --is-inside-work-tree 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        git -C $ProjectPath check-ignore -q -- $Dest
        if ($LASTEXITCODE -eq 1) {
            Write-Warning "$Dest is not git-ignored. Add 'archive/' to .gitignore; the snapshot includes ignored files such as .env."
        }
    }
}

$count = (Get-ChildItem -LiteralPath $Dest -Recurse -File -Force | Measure-Object).Count
Write-Host "Snapshot created: $Dest ($count files)"
exit 0
