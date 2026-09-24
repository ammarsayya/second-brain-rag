# CI-like local check (T-P1-01): lint, format, types, tests, plan consistency. Exit code 0 = green.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

$uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
if (-not $uv) { $uv = Join-Path $env:APPDATA 'Python\Python314\Scripts\uv.exe' }
if (-not (Test-Path $uv)) { throw 'uv not found (install: python -m pip install --user uv)' }

$steps = @(
    @('ruff check', @('run', '--frozen', 'ruff', 'check', 'src', 'tests')),
    @('ruff format', @('run', '--frozen', 'ruff', 'format', '--check', 'src', 'tests')),
    @('mypy', @('run', '--frozen', 'mypy')),
    @('pytest', @('run', '--frozen', 'pytest', '-q')),
    @('validate_plan', @('run', '--frozen', 'python', 'tools/validate_plan.py')),
    @('audit_crossrefs', @('run', '--frozen', 'python', 'tools/audit_crossrefs.py'))
)
$failed = @()
foreach ($s in $steps) {
    Write-Host "==> $($s[0])"
    & $uv @($s[1])
    if ($LASTEXITCODE -ne 0) { $failed += $s[0] }
}
if ($failed.Count -gt 0) { Write-Host "CHECK FAILED: $($failed -join ', ')"; exit 1 }
Write-Host 'CHECK GREEN'
