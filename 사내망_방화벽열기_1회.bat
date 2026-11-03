@echo off
chcp 65001 >nul
net session >nul 2>&1
if %errorlevel% neq 0 (
  echo 관리자 권한이 필요합니다.
  echo 이 파일을 마우스 오른쪽 클릭 - "관리자 권한으로 실행" 하세요.
  pause
  exit /b
)
netsh advfirewall firewall delete rule name="MM-Compass" >nul 2>&1
netsh advfirewall firewall add rule name="MM-Compass" dir=in action=allow protocol=TCP localport=8800 profile=domain,private
echo.
echo 완료: 사내망(도메인/개인 네트워크)에서 8800 포트 접속이 허용되었습니다.
pause
