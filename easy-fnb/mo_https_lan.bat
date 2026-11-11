@echo off
:: Mo may chu bang https tu ky tren mang LAN: dung cho camera dien thoai, KHONG can internet.
:: Lan dau iPhone hien canh bao chung chi: bam Show details > visit this website (Van tiep tuc).
:: Mo tren dien thoai:  https://<ip>:8443/phat?cam=cam1   va   https://<ip>:8443/truc-tiep
cd /d "%~dp0"
set "DATA_DIR=%~dp0.data"
set PYTHONIOENCODING=utf-8
".venv\Scripts\python.exe" -m server --https --port 8443
pause
