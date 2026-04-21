$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"
$uvicornPath = Join-Path $backendDir ".venv\Scripts\uvicorn.exe"
$weightsDir = Join-Path $backendDir "weights"
$logDir = Join-Path $repoRoot "logs"
$logFile = Join-Path $logDir "backend-supervisor.log"

if (!(Test-Path $logDir)) {
  New-Item -ItemType Directory -Path $logDir | Out-Null
}

if (!(Test-Path $uvicornPath)) {
  $message = "[{0}] uvicorn 실행 파일을 찾지 못했습니다: {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $uvicornPath
  Add-Content -Path $logFile -Value $message
  throw $message
}

if (-not $env:FASHN_WEIGHTS_DIR -or [string]::IsNullOrWhiteSpace($env:FASHN_WEIGHTS_DIR)) {
  $env:FASHN_WEIGHTS_DIR = $weightsDir
}

Set-Location $backendDir

while ($true) {
  try {
    $startLog = "[{0}] backend start (host=127.0.0.1 port=8000)" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    Add-Content -Path $logFile -Value $startLog
    & $uvicornPath main:app --host 127.0.0.1 --port 8000
    $exitLog = "[{0}] backend stopped gracefully; restart after 5s" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    Add-Content -Path $logFile -Value $exitLog
  }
  catch {
    $errorLog = "[{0}] backend crashed: {1}; restart after 5s" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $_.Exception.Message
    Add-Content -Path $logFile -Value $errorLog
  }
  Start-Sleep -Seconds 5
}
