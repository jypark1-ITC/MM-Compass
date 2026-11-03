@echo off
chcp 65001 >nul
cd /d %~dp0
if not exist .venv\Scripts\python.exe (
  echo 먼저 시작.bat 을 한 번 실행해서 설치를 끝내 주세요.
  pause
  exit /b
)
echo.
echo ===== MM-Compass 사내망 모드 =====
echo 아래 IPv4 주소 중 사내망 주소를 확인하세요.
echo 담당자 접속 주소:  http://IP주소:8800
echo 이 창을 닫으면 사이트가 꺼집니다.
echo.
ipconfig | findstr /i "IPv4"
echo.
.venv\Scripts\python app.py --lan
pause
