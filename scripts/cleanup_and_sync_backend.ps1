$ErrorActionPreference = "Stop"

Write-Host "`nQuivrr backend cleanup and sync starting..." -ForegroundColor Cyan

$repoRoot = Resolve-Path "."
Set-Location $repoRoot

if (-not (Test-Path ".git")) {
    throw "This folder is not a Git repository. Run this from quivrr-backend."
}

Write-Host "`nCreating folders..." -ForegroundColor Cyan

New-Item -ItemType Directory -Force -Path ".\scripts" | Out-Null
New-Item -ItemType Directory -Force -Path ".\scrapers\brands\devtools" | Out-Null
New-Item -ItemType Directory -Force -Path ".\scrapers\products\devtools" | Out-Null
New-Item -ItemType Directory -Force -Path ".\scrapers\common" | Out-Null

Write-Host "`nMoving temporary inspection/debug scripts..." -ForegroundColor Cyan

$brandDevTools = @(
    ".\scrapers\brands\debug_js_product.py",
    ".\scrapers\brands\inspect_js_outputs.py",
    ".\scrapers\brands\inspect_js_product_structure.py"
)

foreach ($file in $brandDevTools) {
    if (Test-Path $file) {
        Move-Item -Path $file -Destination ".\scrapers\brands\devtools\" -Force
    }
}

$productDevTools = @(
    ".\scrapers\products\patch_daily_refresh_add_woocommerce.py",
    ".\scrapers\products\patch_js_inventory_matcher.py"
)

foreach ($file in $productDevTools) {
    if (Test-Path $file) {
        Move-Item -Path $file -Destination ".\scrapers\products\devtools\" -Force
    }
}

Write-Host "`nRemoving cache and logs..." -ForegroundColor Cyan

Get-ChildItem . -Recurse -Directory -Force |
Where-Object { $_.Name -eq "__pycache__" -and $_.FullName -notlike "*\venv\*" } |
ForEach-Object {
    Remove-Item $_.FullName -Recurse -Force
}

Get-ChildItem . -Recurse -File -Force |
Where-Object { $_.Extension -eq ".pyc" -and $_.FullName -notlike "*\venv\*" } |
ForEach-Object {
    Remove-Item $_.FullName -Force
}

$logFolders = @(
    ".\logs",
    ".\scrapers\products\logs",
    ".\scrapers\retailers\stockists\logs"
)

foreach ($folder in $logFolders) {
    if (Test-Path $folder) {
        Remove-Item $folder -Recurse -Force
    }
}

Write-Host "`nWriting .gitignore..." -ForegroundColor Cyan

@"
# Python
venv/
__pycache__/
*.pyc
*.pyo
*.pyd

# Logs
logs/
*.log
scrapers/products/logs/
scrapers/retailers/stockists/logs/

# Generated scrape output
scrapers/products/output/
scrapers/retailers/stockists/output/

# Raw downloaded stockist pages
scrapers/retailers/stockists/raw/

# Local OS/editor files
.DS_Store
Thumbs.db
.vscode/
"@ | Set-Content ".\.gitignore" -Encoding UTF8

Write-Host "`nAdding placeholder for shared parser module..." -ForegroundColor Cyan

if (-not (Test-Path ".\scrapers\common\__init__.py")) {
    New-Item -ItemType File -Path ".\scrapers\common\__init__.py" | Out-Null
}

if (-not (Test-Path ".\scrapers\common\README.md")) {
@"
# Common scraper utilities

This folder will hold shared parsing and normalisation logic used across brands and retailers.

Planned modules:
- board_parser.py
- dimensions.py
- normaliser.py
- matching.py
"@ | Set-Content ".\scrapers\common\README.md" -Encoding UTF8
}

Write-Host "`nCurrent Git status:" -ForegroundColor Yellow
git status --short

Write-Host "`nReview the status above before continuing." -ForegroundColor Yellow
$confirm = Read-Host "Commit and push these cleanup changes to GitHub? Type Y to continue"

if ($confirm -ne "Y") {
    Write-Host "`nStopped before commit. No Git sync completed." -ForegroundColor Yellow
    exit 0
}

git add .

git commit -m "clean scraper structure and add JS catalogue workflow"

git push origin main

Write-Host "`nCleanup complete and pushed to GitHub." -ForegroundColor Green
Write-Host "Azure will update only if the backend repo has a GitHub Actions deployment workflow connected." -ForegroundColor Green
