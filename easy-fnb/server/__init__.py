"""Máy chủ Easy FnB.

Nạp tệp .env (nếu có) ngay khi gói được nạp, trước mọi module đọc biến môi trường. Nhờ vậy muốn bật
Gemini chỉ cần chép .env.example thành .env rồi dán khoá vào, không phải đặt biến môi trường bằng tay.
Biến đã đặt sẵn trong môi trường (ví dụ trên Cloud Run) luôn thắng tệp .env.
"""
import os
from pathlib import Path


def nap_env(path):
    """Đọc các dòng TEN=gia_tri. Trả về tên những biến vừa đặt."""
    da_dat = []
    try:
        lines = Path(path).read_text(encoding='utf-8-sig').splitlines()
    except OSError:
        return da_dat
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        ten, gia_tri = line.split('=', 1)
        ten, gia_tri = ten.strip().removeprefix('export ').strip(), gia_tri.strip()
        if len(gia_tri) >= 2 and gia_tri[0] == gia_tri[-1] and gia_tri[0] in '"\'':
            gia_tri = gia_tri[1:-1]
        if ten and gia_tri and not os.environ.get(ten):
            os.environ[ten] = gia_tri
            da_dat.append(ten)
    return da_dat


nap_env(Path(__file__).resolve().parent.parent / '.env')
