# n8n 및 터미널 환경 복구 스크립트

$nodejsPath = "C:\Program Files\nodejs"
$pythonPath = "C:\Users\User\AppData\Local\Programs\Python\Python312"
$npmPath = "C:\Users\User\AppData\Roaming\npm"

# 1. 현재 세션 경로 추가
$env:PATH = "$nodejsPath;$pythonPath;$pythonPath\Scripts;$npmPath;" + $env:PATH

# 2. 영구 환경 변수 등록 (중복 방지)
$currentUserPath = [Environment]::GetEnvironmentVariable("PATH", "User")
$newPaths = @($nodejsPath, $pythonPath, "$pythonPath\Scripts", $npmPath)
foreach ($p in $newPaths) {
    if ($currentUserPath -notlike "*$p*") {
        $currentUserPath = "$p;$currentUserPath"
    }
}
[Environment]::SetEnvironmentVariable("PATH", $currentUserPath, "User")

# 3. 실행 정책 설정
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force

# 4. 고장난 n8n 삭제 및 재설치 시도 (npx 권장)
Write-Host "고장난 n8n 구성을 정리합니다..." -ForegroundColor Cyan
if (Test-Path "$npmPath\node_modules\n8n") {
    Remove-Item -Path "$npmPath\node_modules\n8n" -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "설정 완료! 이제 'node -v'와 'python --version'이 작동할 것입니다." -ForegroundColor Green
Write-Host "중요: 현재 터미널 창을 닫고 새로 열어야 환경 변수가 완전히 적용됩니다." -ForegroundColor Yellow
