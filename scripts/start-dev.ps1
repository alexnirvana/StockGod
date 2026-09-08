param([switch]$Install)
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$pythonExe = Join-Path $projectRoot ".venv/Scripts/python.exe"
if (!(Test-Path -LiteralPath $pythonExe)) {
    python -m venv .venv
    $Install = $true
}
if ($Install) {
    & $pythonExe -m pip install -r backend/requirements.lock
    if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed." }
    & $pythonExe -m pip install --no-deps -e backend
    Push-Location frontend
    try { npm.cmd ci; if ($LASTEXITCODE -ne 0) { throw "npm ci failed." } } finally { Pop-Location }
}
& $pythonExe -m alembic -c backend/alembic.ini upgrade head
if ($LASTEXITCODE -ne 0) { throw "Database migration failed." }
$children = @()
try {
    $children += Start-Process -FilePath $pythonExe -ArgumentList "-m","uvicorn","stock_god.api.main:app","--host","127.0.0.1","--port","8000" -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru
    Start-Sleep -Seconds 2
    $children += Start-Process -FilePath $pythonExe -ArgumentList "-m","stock_god.jobs.worker" -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru
    Write-Host "Stock God: http://127.0.0.1:5173 — Ctrl+C to stop."
    Push-Location frontend
    try { npm.cmd run dev } finally { Pop-Location }
} finally {
    foreach ($child in $children) { if (!$child.HasExited) { Stop-Process -Id $child.Id -ErrorAction SilentlyContinue } }
}

