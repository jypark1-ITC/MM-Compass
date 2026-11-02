@echo off
chcp 65001 >nul
cd /d %~dp0
if not exist .venv (
  echo [1/2] 처음 실행: 필요한 프로그램을 설치합니다...
  py -m venv .venv
  .venv\Scripts\python -m pip install -r requirements.txt
)
fc /b requirements.txt .venv\req.txt >nul 2>&1 || (
  echo 필요한 프로그램을 확인·설치합니다...
  .venv\Scripts\python -m pip install -r requirements.txt && copy /y requirements.txt .venv\req.txt >nul
)
if not exist storage\gadong.db (
  echo [2/2] 관리자 계정을 만듭니다.
  .venv\Scripts\python manage.py init
)
start "" http://127.0.0.1:8800
.venv\Scripts\python app.py
pause
