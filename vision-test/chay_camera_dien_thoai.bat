@echo off
:: Chay camera AI doc luong tu dien thoai (trang /phat). Mo trang /phat tren iPhone truoc, bam "Bat dau phat".
::   chay_camera_dien_thoai.bat [ma camera] [may chu]
setlocal
set "CAM=%~1"
if "%CAM%"=="" set "CAM=cam1"
set "URL=%~2"
if "%URL%"=="" set "URL=http://localhost:8080"
call "%~dp0chay_camera.bat" %URL%/api/phone/%CAM%/mjpeg %URL% %CAM%