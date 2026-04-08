# Build a single-file Windows executable (logo bundled; place serviceAccountKey.json beside the .exe).
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path "logo.png")) {
    Write-Error "logo.png must exist in the project root."
}

if (-not (Test-Path "logo.ico")) {
    Write-Error "logo.ico must exist in the project root (no auto-conversion)."
}

python -m PyInstaller --noconfirm --clean dawa_whatsapp.spec
Write-Host ""
Write-Host "Built: dist\DawaWhatsApp.exe"
Write-Host "Copy serviceAccountKey.json next to the exe if you use Firebase."

