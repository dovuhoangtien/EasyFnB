@echo off
:: Chay camera AI (ban v5 demo) va gui len app Easy FnB.
::   chay_camera.bat [nguon] [may chu] [ma camera]
::   nguon   : file video (chay lap lai), so webcam (0), hoac rtsp://...  Mac dinh: clips\01_phong_an_goc_cao.mp4
::   may chu : mac dinh http://localhost:8080. Cloud Run co dat EDGE_KEY thi dat bien EDGE_KEY truoc khi chay.
::   ma camera: mac dinh cam1 (vung ban ve tren web gan voi ma nay)
:: Them tham so khac sau 3 tham so tren, vi du: chay_camera.bat 0 http://localhost:8080 cam1 --device cpu
setlocal
chcp 65001 >nul
:: Python in tiếng Việt ra console: thiếu dòng này thì gặp lỗi charmap/cp1252 và tắt giữa chừng.
set "PYTHONIOENCODING=utf-8"
cd /d %~dp0

:: Python của pipeline. Ưu tiên venv trong dự án; nếu chưa có thì dùng venv dùng chung
:: ở %USERPROFILE%\.easy-fnb\venv (đường dẫn ngắn, vì torch không nạp được DLL khi
:: đường dẫn quá dài); cuối cùng mới đến python trong PATH.
set "PY=venv\Scripts\python.exe"
if exist "%PY%" goto :co_py
set "PY=%USERPROFILE%\.easy-fnb\venv\Scripts\python.exe"
if exist "%PY%" goto :co_py
set "PY=python"
:co_py

set "SRC=%~1"
if "%SRC%"=="" set "SRC=clips\01_phong_an_goc_cao.mp4"
set "URL=%~2"
if "%URL%"=="" set "URL=http://localhost:8080"
set "CAM=%~3"
if "%CAM%"=="" set "CAM=cam1"
set "MORE="
if exist "%SRC%" set "MORE=--lap"
shift & shift & shift
set "REST="
:gom
if "%~1"=="" goto :chay
set "REST=%REST% %1"
shift
goto :gom

:chay
"%PY%" easyfnb_test.py "%SRC%" --may-chu %URL% --camera %CAM% --thoi-gian-thuc %MORE% --no-video ^
  --hand-model giotay_pe_b16.pt --hand-th 0.35 --staff-model nhanvien_pe_b16.pt ^
  --table-model clip --clip-backbone pe_core_s16 ^
  --pose-models yolo26n-pose_544x960_fp16.engine --det-models yolo26s_736x1280_fp16.engine ^
  --pose-refine rtmpose-m --refine-mode luot --det-every 100 --staff-every 20 --tich-luy --yoloe --hanh-dong %REST%
