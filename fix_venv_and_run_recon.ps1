$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "Quivrr backend venv repair and retailer recon runner"
Write-Host "===================================================="
Write-Host ""

$ProjectRoot = "C:\Projects\quivrr.app\quivrr-backend"
$VenvPath = Join-Path $ProjectRoot "venv"
$PythonExe = Join-Path $VenvPath "Scripts\python.exe"
$ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
$ReconScript = Join-Path $ProjectRoot "scripts\tools\retailer_recon_probe.py"

Set-Location $ProjectRoot

Write-Host "Project root:"
Write-Host $ProjectRoot
Write-Host ""

if (Test-Path $VenvPath) {
    Write-Host "Removing old venv..."
    Remove-Item -Recurse -Force $VenvPath
}

Write-Host "Creating new venv..."
py -3.13 -m venv venv

if (!(Test-Path $PythonExe)) {
    Write-Host "Python 3.13 venv creation failed. Trying default python..."
    python -m venv venv
}

if (!(Test-Path $PythonExe)) {
    throw "Could not create venv. Python is not available from py or python."
}

Write-Host "Upgrading pip..."
& $PythonExe -m pip install --upgrade pip

Write-Host "Installing backend requirements if requirements.txt exists..."
if (Test-Path ".\requirements.txt") {
    & $PythonExe -m pip install -r .\requirements.txt
}

Write-Host "Installing recon dependencies..."
& $PythonExe -m pip install httpx beautifulsoup4 lxml

Write-Host ""
Write-Host "Checking imports..."
& $PythonExe -c "import httpx, bs4, lxml; print('Imports OK')"

Write-Host ""
Write-Host "Python being used:"
& $PythonExe -c "import sys; print(sys.executable)"

Write-Host ""
Write-Host "Running retailer recon..."
& $PythonExe $ReconScript --rounds 3 --delay 120

Write-Host ""
Write-Host "Done."
Write-Host "Check the newest retailer_recon_results folder in:"
Write-Host $ProjectRoot