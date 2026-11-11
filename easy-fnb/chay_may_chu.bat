@echo off
:: Chay may chu Easy FnB + web app tren cong 8080 (bam dup la chay).
:: Lan dau tu cai thu vien va build web. Gemini: dat bien moi truong GEMINI_API_KEY truoc.
setlocal
chcp 65001 >nul
cd /d %~dp0

if not exist .venv\Scripts\python.exe (
  echo [1/3] Tao moi truong Python...
  python -m venv .venv || goto :loi
  .venv\Scripts\python -m pip install -q -r server\requirements.txt || goto :loi
)
if not exist node_modules (
  echo [2/3] Cai thu vien web...
  call npm ci --no-audit --no-fund || goto :loi
)
if not exist dist\index.html (
  echo [3/3] Build web app...
  call npm run build || goto :loi
)
if "%GEMINI_API_KEY%"=="" echo Chua co GEMINI_API_KEY: app van chay, chi khong co Gemini kiem tra anh va tro ly.
.venv\Scripts\python -m server %*
goto :eof

:loi
echo Loi, xem dong bao loi o tren.
pause
