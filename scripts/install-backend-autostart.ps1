$ErrorActionPreference = "Stop"

$taskName = "AI-Fitting-Backend-Autostart"
$scriptPath = Join-Path $PSScriptRoot "run-backend-forever.ps1"
$escapedScriptPath = $scriptPath.Replace('"', '\"')
$taskCommand = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$escapedScriptPath`""

try {
  schtasks /Delete /TN $taskName /F | Out-Null
}
catch {
  # 기존 작업이 없으면 무시
}

schtasks /Create /TN $taskName /TR $taskCommand /SC ONLOGON /F | Out-Null
schtasks /Run /TN $taskName | Out-Null

Write-Host "작업 스케줄러 등록 완료: $taskName"
Write-Host "로그 파일: $(Join-Path (Split-Path -Parent $PSScriptRoot) 'logs\backend-supervisor.log')"
