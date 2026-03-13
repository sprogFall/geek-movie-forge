Param(
  [switch]$Volumes
)

$ErrorActionPreference = "Stop"

$rootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $rootDir

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  throw "docker not found."
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
    throw "docker compose not available."
  }
}

$composeArgs = @()
$composeArgs += $composePrefix
$composeArgs += @("down")
if ($Volumes) { $composeArgs += "--volumes" }

Write-Host "Stopping stack..."
Write-Host "Compose: $composeExe $($composeArgs -join ' ')"

& $composeExe @composeArgs

