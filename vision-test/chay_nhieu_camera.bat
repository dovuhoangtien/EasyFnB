@echo off
:: Chay camera AI cho nhieu dien thoai cung luc, moi camera mot cua so rieng.
::   chay_nhieu_camera.bat cam1 cam2 cam3
:: Moi ma camera doc hinh tu dien thoai da mo trang /phat?cam=<ma>. Khong ghi ma nao thi chay cam1.
:: May chu mac dinh http://127.0.0.1:8080; dat bien MAY_CHU truoc neu khac.
:: GPU 4 GB chay thoai mai 1 camera; 2 camera tro len thi moi camera cham hon (it khung/giay hon).
setlocal
chcp 65001 >nul
cd /d %~dp0
if "%MAY_CHU%"=="" set "MAY_CHU=http://127.0.0.1:8080"
if "%~1"=="" (
  start "Camera AI cam1" cmd /k chay_camera.bat %MAY_CHU%/api/phone/cam1/mjpeg %MAY_CHU% cam1 --nv-theo-anh --nhin-quanh
  goto :eof
)
:moi
if "%~1"=="" goto :eof
start "Camera AI %~1" cmd /k chay_camera.bat %MAY_CHU%/api/phone/%~1/mjpeg %MAY_CHU% %~1 --nv-theo-anh --nhin-quanh
shift
goto :moi
