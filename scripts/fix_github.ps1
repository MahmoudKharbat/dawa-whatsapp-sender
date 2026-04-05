#Requires -Version 5.1
<#
  Connects to GitHub, creates the private repo if it does not exist, and pushes this project.

  Option A — Personal access token (good for automation / Cursor):
    1. Create a classic PAT: https://github.com/settings/tokens  (enable "repo")
    2. Either:
         $env:GH_TOKEN = "ghp_xxxxxxxx"
       Or save the token only in project root file: gh_token.txt  (this file is gitignored)
    3. Run:  powershell -ExecutionPolicy Bypass -File scripts\fix_github.ps1

  Option B — Browser login:
    Run:  gh auth login -h github.com -p https -w
    Then run this script again (no token needed).
#>
$ErrorActionPreference = "Stop"
$Repo = "MahmoudKharbat/dawa-whatsapp-sender"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

$ghCmd = Get-Command gh -ErrorAction SilentlyContinue
$gh = if ($ghCmd) { $ghCmd.Source } else { $null }
if (-not $gh) {
    $gh = "C:\Program Files\GitHub CLI\gh.exe"
}
if (-not (Test-Path $gh)) {
    Write-Error "GitHub CLI (gh) not found. Install: winget install GitHub.cli"
}

function Ensure-GhAuth {
    & $gh auth status 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { return }

    $token = $env:GH_TOKEN
    if (-not $token) {
        $tf = Join-Path $ProjectRoot "gh_token.txt"
        if (Test-Path $tf) {
            $token = (Get-Content $tf -Raw).Trim()
        }
    }
    if ($token) {
        $token | & $gh auth login --hostname github.com --with-token
        if ($LASTEXITCODE -ne 0) { Write-Error "gh auth login --with-token failed." }
        return
    }

    Write-Host "Not logged in. Opening GitHub login (browser)..." -ForegroundColor Yellow
    & $gh auth login -h github.com -p https -w
    if ($LASTEXITCODE -ne 0) { Write-Error "gh auth login failed." }
}

Ensure-GhAuth
& $gh auth setup-git
if ($LASTEXITCODE -ne 0) { Write-Error "gh auth setup-git failed." }

& $gh repo view $Repo 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating private repository $Repo ..." -ForegroundColor Cyan
    $createOut = & $gh repo create $Repo --private -d "Dawa WhatsApp bulk sender and contact CRM" 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) {
        if ($createOut -match "already exists|Name already") {
            Write-Host "Repository already exists; continuing." -ForegroundColor Green
        } else {
            Write-Error "gh repo create failed: $createOut"
        }
    }
} else {
    Write-Host "Repository $Repo already exists on GitHub." -ForegroundColor Green
}

$remote = (& git remote get-url origin 2>$null)
if (-not $remote) {
    Write-Error "No git remote 'origin'. Add: git remote add origin https://github.com/$Repo.git"
}
$expected = "github.com/MahmoudKharbat/dawa-whatsapp-sender"
if ($remote -notmatch [regex]::Escape("MahmoudKharbat/dawa-whatsapp-sender")) {
    Write-Warning "origin URL is:`n  $remote`nExpected path containing MahmoudKharbat/dawa-whatsapp-sender"
}

$branch = (git branch --show-current).Trim()
if (-not $branch) { Write-Error "Could not detect current branch." }

Write-Host "Pushing branch '$branch' to origin ..." -ForegroundColor Cyan
git push -u origin $branch
if ($LASTEXITCODE -ne 0) { Write-Error "git push failed." }

Write-Host "Done. Remote: https://github.com/$Repo" -ForegroundColor Green
