@echo off
:: Chay thu bang video CCTV that tai ve tu mang (khong can camera, khong can tu quay).
::   chay_video_mau.bat [so] [may chu]
::   so: 1..17, xem danh sach ben duoi. Mac dinh 1.
:: Video chay lap lai lien tuc (--lap) de demo tai cho.
:: Truoc khi chay, nap vung ban ve san cua clip (neu co) len may chu cho camera cam1.
setlocal
chcp 65001 >nul
:: Python in tiếng Việt ra console: thiếu dòng này thì gặp lỗi charmap/cp1252 và tắt giữa chừng.
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0"

:: Python của pipeline: venv trong dự án, rồi venv dùng chung (đường dẫn ngắn vì torch
:: không nạp được DLL khi đường dẫn quá dài), cuối cùng là python trong PATH.
set "PY=venv\Scripts\python.exe"
if exist "%PY%" goto :co_py
set "PY=%USERPROFILE%\.easy-fnb\venv\Scripts\python.exe"
if exist "%PY%" goto :co_py
set "PY=python"
:co_py

set "N=%~1"
if "%N%"=="" set "N=1"
set "URL=%~2"
if "%URL%"=="" set "URL=http://localhost:8080"

if "%N%"=="1" set "F=m01_bbq_vn_ban_an.mp4"
if "%N%"=="2" set "F=m02_bbq_han_dong_khach.mp4"
if "%N%"=="3" set "F=m03_cafe_san_vuon_vn.mp4"
if "%N%"=="4" set "F=m04_cafe_quay_pa.mp4"
if "%N%"=="5" set "F=m05_nha_hang_san_vuon_ptz.mp4"
if "%N%"=="6" set "F=m06_ban_an_tren_cao.mp4"
if "%N%"=="7" set "F=m07_cctv_den_trang.mp4"
if "%N%"=="8" set "F=m08_quan_an_vn_nv_ao_den.mp4"
if "%N%"=="9" set "F=m09_quan_com_vn_dong_khach_7phut.mp4"
if "%N%"=="10" set "F=m10_cafe_vn_khach_ve_nv_don_ban_6phut.mp4"
if "%N%"=="11" set "F=m11_cafe_vn_nv_ao_xanh_phuc_vu.mp4"
if "%N%"=="12" set "F=m12_quan_nhau_vn_rat_dong_dem.mp4"
if "%N%"=="13" set "F=m13_quan_an_da_nang_goc_cao.mp4"
if "%N%"=="14" set "F=m14_quan_nhau_vn_ban_ban_chua_don.mp4"
if "%N%"=="15" set "F=m15_cafe_vn_khach_ngoi_yen.mp4"
if "%N%"=="16" set "F=m16_cafe_vn_ban_trong_nguoi_di_qua.mp4"
if "%N%"=="17" set "F=m17_cafe_vn_quay_led_ngan.mp4"

if not exist "video_mang\%F%" (
  echo Khong thay video_mang\%F%
  echo 1 = BBQ Viet co nhan vien va khach gio tay  2 = BBQ Han rat dong
  echo 3 = cafe san vuon   4 = cafe quay pha che   5 = nha hang san vuon PTZ
  echo 6 = ban an nhin tu tren cao   7 = CCTV den trang
  echo 8 = quan an VN, nhan vien ao den   9 = quan com dong khach 7 phut
  echo 10 = cafe VN: khach ve, nhan vien don ban (hay nhat)   11 = cafe, nhan vien ao xanh
  echo 12 = quan nhau rat dong ban dem   13 = quan an Da Nang   14 = ban ban chua don
  echo 15 = khach ngoi yen (khong duoc bao gi)   16 = ban trong, nguoi di qua   17 = cafe nho
  exit /b 1
)
echo Dang chay video mau %N%: %F%
"%PY%" nap_vung_ban.py "%F:.mp4=%" %URL% --camera cam1
call "%~dp0chay_camera.bat" "video_mang\%F%" %URL% cam1
