Param(
  [switch]$Full,
  [switch]$Detach,
  [switch]$Automation,
  [switch]$Open
)

$ErrorActionPreference = "Stop"

function Show-Help {
  Write-Host @"
Usage:
  powershell -ExecutionPolicy Bypass -File scripts/dev-up.ps1 [-Full] [-Detach] [-Automation] [-Open]

Starts Geek Movie Forge local stack via Docker Compose.

Defaults:
  Minimal (starts web + api + their dependencies)

Options:
  -Full         Start all services in docker-compose.yml (workers, orchestrator, minio, remotion, etc).
  -Detach       Run containers in the background.
  -Automation   Also enable the "automation" profile (n8n).
  -Open         Open http://localhost:3000 after starting.
"@
}

if ($args -contains "-h" -or $args -contains "--help") {
  Show-Help
  exit 0
}

$rootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $rootDir

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  throw "docker not found. Install Docker Desktop first."
}

$composeExe = $null
& docker compose version *> $null
if ($LASTEXITCODE -eq 0) {
  $composeExe = "docker"
  $composePrefix = @("compose")
} else {
  if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
    $composeExe = "docker-compose"
    $composePrefix = @()
  } else {
    throw "docker compose not available. Install a recent Docker Desktop or docker-compose."
  }
}

& docker info *> $null
if ($LASTEXITCODE -ne 0) {
  throw "Docker daemon is not running. Start Docker Desktop and retry."
}

if (-not (Test-Path ".env")) {
  if (-not (Test-Path ".env.example")) {
    throw ".env is missing and .env.example was not found."
  }
  Copy-Item ".env.example" ".env"
  Write-Host "Created .env from .env.example"
}

$jwtLine = Select-String -Path ".env" -Pattern '^JWT_SECRET=' -SimpleMatch | Select-Object -Last 1
if (-not $jwtLine) {
  throw "JWT_SECRET is missing in .env (required, min 32 chars)."
}
$jwtSecret = ($jwtLine.Line -replace '^JWT_SECRET=', '')
$jwtSecret = $jwtSecret.Trim('"')
if ($jwtSecret.Length -lt 32) {
  throw "JWT_SECRET in .env must be at least 32 characters (current: $($jwtSecret.Length))."
}

$profileArgs = @()
if ($Automation) {
  $profileArgs = @("--profile", "automation")
}

$composeArgs = @()
$composeArgs += $composePrefix
$composeArgs += $profileArgs
$composeArgs += @("up", "--build")
if ($Detach) { $composeArgs += "-d" }

if (-not $Full) {
  $composeArgs += @("api", "web")
}

Write-Host "Starting stack: $((if ($Full) { 'full' } else { 'minimal' }))"
Write-Host "Compose: $composeExe $($composeArgs -join ' ')"

& $composeExe @composeArgs

if ($Detach) {
  Write-Host ""
  Write-Host "Frontend: http://localhost:3000"
  Write-Host "API:      http://localhost:8000  (health: /healthz, docs: /docs)"
  Write-Host ""
  Write-Host "Logs:     $composeExe $($composePrefix -join ' ') logs -f --tail=200"
  Write-Host "Stop:     powershell -ExecutionPolicy Bypass -File scripts/dev-down.ps1"
}

if ($Open) {
  try {
    Start-Process "http://localhost:3000" | Out-Null
  } catch {
    # Best effort
  }
}

