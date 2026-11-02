@echo off
chcp 65001 >nul
cd /d %~dp0
if not exist .venv (
  echo 먼저 시작.bat 을 한 번 실행해 주세요.
  pause
  exit /b
)
echo === 가동ON 비밀번호 재설정 ===
.venv\Scripts\python manage.py resetpw
pause
