[CmdletBinding()]
param(
    [switch]$CheckOnly,
    [switch]$NoBrowser
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $projectRoot "backend"
$frontendDir = Join-Path $projectRoot "frontend"
$jobPageUrl = "http://localhost:5173/stage3/jobs"
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

function Assert-Command {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$InstallHint
    )

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Missing command '$Name'. $InstallHint"
    }
}

function Invoke-NativeCommand {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$FailureMessage
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw $FailureMessage
    }
}

function Test-ListeningPort {
    param([Parameter(Mandatory = $true)][int]$Port)

    try {
        return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop)
    }
    catch {
        return $false
    }
}

function Start-DevelopmentWindow {
    param(
        [Parameter(Mandatory = $true)][string]$Title,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [Parameter(Mandatory = $true)][string]$Command
    )

    $escapedTitle = $Title.Replace("'", "''")
    $escapedDirectory = $WorkingDirectory.Replace("'", "''")
    $windowScript = @"
try { `$Host.UI.RawUI.WindowTitle = '$escapedTitle' } catch { }
Set-Location -LiteralPath '$escapedDirectory'
$Command
"@
    $encodedCommand = [Convert]::ToBase64String(
        [Text.Encoding]::Unicode.GetBytes($windowScript)
    )

    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoLogo",
        "-NoProfile",
        "-NoExit",
        "-ExecutionPolicy",
        "Bypass",
        "-EncodedCommand",
        $encodedCommand
    ) | Out-Null
}

function Wait-ForUrl {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$ServiceName,
        [int]$Attempts = 30
    )

    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        try {
            Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 | Out-Null
            return
        }
        catch {
            Start-Sleep -Seconds 1
        }
    }

    throw "$ServiceName did not become ready. Check its server window for the detailed error."
}

foreach ($requiredFile in @(
    (Join-Path $projectRoot "docker-compose.yml"),
    (Join-Path $backendDir "alembic.ini"),
    (Join-Path $backendDir "requirements.txt"),
    (Join-Path $frontendDir "package.json")
)) {
    if (-not (Test-Path -LiteralPath $requiredFile)) {
        throw "Required project file not found: $requiredFile"
    }
}

Assert-Command -Name "docker" -InstallHint "Install and open Docker Desktop first."
Assert-Command -Name "node" -InstallHint "Install Node.js 18 or newer first."
Assert-Command -Name "npm.cmd" -InstallHint "Install Node.js with npm first."

if (Test-Path -LiteralPath $venvPython) {
    $pythonCommand = $venvPython
}
else {
    Assert-Command -Name "python" -InstallHint "Install Python 3.9 or newer first."
    $pythonCommand = (Get-Command "python").Source
}

if ($CheckOnly) {
    Write-Host "Startup script check passed." -ForegroundColor Green
    Write-Host "Project root: $projectRoot"
    Write-Host "Python: $pythonCommand"
    Write-Host "Run launch\start_project.bat to start the project."
    exit 0
}

Write-Host "[1/5] Checking Docker Desktop..." -ForegroundColor Cyan
& docker info *> $null
if ($LASTEXITCODE -ne 0) {
    $dockerDesktopPath = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
    if (-not (Test-Path -LiteralPath $dockerDesktopPath)) {
        throw "Docker Desktop is not running. Open Docker Desktop, wait until it is ready, then run this script again."
    }

    Write-Host "Starting Docker Desktop. This can take about one minute..."
    Start-Process -FilePath $dockerDesktopPath -WindowStyle Hidden | Out-Null
    $dockerReady = $false
    for ($attempt = 1; $attempt -le 60; $attempt++) {
        Start-Sleep -Seconds 2
        & docker info *> $null
        if ($LASTEXITCODE -eq 0) {
            $dockerReady = $true
            break
        }
    }
    if (-not $dockerReady) {
        throw "Docker Desktop did not become ready. Open it manually, then run this script again."
    }
}

Write-Host "[2/5] Starting PostgreSQL, Redis, and Chroma..." -ForegroundColor Cyan
Push-Location $projectRoot
try {
    Invoke-NativeCommand -Command "docker" -Arguments @(
        "compose", "up", "-d", "postgres", "redis", "chroma"
    ) -FailureMessage "Docker infrastructure failed to start."

    $postgresReady = $false
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        & docker compose exec -T postgres pg_isready -U postgres -d recruitment_assistant *> $null
        if ($LASTEXITCODE -eq 0) {
            $postgresReady = $true
            break
        }
        Start-Sleep -Seconds 1
    }
    if (-not $postgresReady) {
        throw "PostgreSQL did not become ready. Check Docker Desktop for details."
    }
}
finally {
    Pop-Location
}

Write-Host "[3/5] Preparing the backend database..." -ForegroundColor Cyan
Push-Location $backendDir
try {
    $previousErrorPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    & $pythonCommand -c "import fastapi, uvicorn, alembic, asyncpg" *> $null
    $dependencyCheckExitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousErrorPreference
    if ($dependencyCheckExitCode -ne 0) {
        Write-Host "Installing missing backend dependencies..."
        Invoke-NativeCommand -Command $pythonCommand -Arguments @(
            "-m", "pip", "install", "-r", "requirements.txt"
        ) -FailureMessage "Backend dependency installation failed."
    }

    Invoke-NativeCommand -Command $pythonCommand -Arguments @(
        "-m", "alembic", "upgrade", "head"
    ) -FailureMessage "PostgreSQL migration failed."
}
finally {
    Pop-Location
}

Write-Host "[4/5] Preparing the frontend..." -ForegroundColor Cyan
if (-not (Test-Path -LiteralPath (Join-Path $frontendDir "node_modules"))) {
    Push-Location $frontendDir
    try {
        Invoke-NativeCommand -Command "npm.cmd" -Arguments @(
            "install"
        ) -FailureMessage "Frontend dependency installation failed."
    }
    finally {
        Pop-Location
    }
}

if (Test-ListeningPort -Port 8000) {
    Write-Host "Backend port 8000 is already running; it will be reused."
}
else {
    $escapedPythonCommand = $pythonCommand.Replace("'", "''")
    Start-DevelopmentWindow `
        -Title "AI Recruitment Assistant - Backend" `
        -WorkingDirectory $backendDir `
        -Command "& '$escapedPythonCommand' -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
}

if (Test-ListeningPort -Port 5173) {
    Write-Host "Frontend port 5173 is already running; it will be reused."
}
else {
    Start-DevelopmentWindow `
        -Title "AI Recruitment Assistant - Frontend" `
        -WorkingDirectory $frontendDir `
        -Command "npm.cmd run dev -- --host 127.0.0.1"
}

Write-Host "[5/5] Waiting for the project page..." -ForegroundColor Cyan
Wait-ForUrl -Url "http://127.0.0.1:8000/api/health" -ServiceName "Backend"
Wait-ForUrl -Url "http://127.0.0.1:5173" -ServiceName "Frontend"

Write-Host "Project is ready." -ForegroundColor Green
Write-Host "Frontend: $jobPageUrl"
Write-Host "API docs: http://localhost:8000/docs"
Write-Host "To stop the frontend/backend, press Ctrl+C in their two server windows."

if (-not $NoBrowser) {
    Start-Process $jobPageUrl | Out-Null
}
