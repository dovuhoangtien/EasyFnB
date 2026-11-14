"""Bật/tắt máy camera AI (vision-test/chay_camera.bat) ngay từ trang web, khi máy chủ chạy cùng máy với camera.

Nguồn hình: điện thoại đang phát ở /phat?cam=<ma> thì dùng điện thoại; không thì chạy lặp video mẫu.
Trên Cloud Run không có thư mục vision-test nên nút này tắt (available=False).
"""
import os
import subprocess
import sys
import time
from pathlib import Path

GOC = Path(__file__).resolve().parents[2] / 'vision-test'
BAT = GOC / 'chay_camera.bat'
VIDEO_MAU = 'clips\\01_phong_an_goc_cao.mp4'

_proc: subprocess.Popen | None = None
_info: dict = {}


def available():
    return sys.platform == 'win32' and BAT.exists() and not os.environ.get('K_SERVICE')


def running():
    return _proc is not None and _proc.poll() is None


def status():
    on = running()
    return dict(available=available(), running=on,
                source=_info.get('source') if on else None, camera=_info.get('camera') if on else None,
                started_at=_info.get('started_at') if on else None)


def start(cam='cam1', phone_live=False):
    """Mở cửa sổ camera AI mới. Đang chạy rồi thì giữ nguyên."""
    global _proc, _info
    if not available():
        raise RuntimeError('Máy này không chạy được camera AI (chỉ có trên máy Windows có thư mục vision-test)')
    if running():
        return status()
    port = os.environ.get('EASYFNB_PORT') or '8080'
    may_chu = f'http://127.0.0.1:{port}'
    if phone_live:
        src, them, nguon = f'{may_chu}/api/phone/{cam}/mjpeg', ['--nv-theo-anh', '--nhin-quanh'], 'phone'
    else:
        src, them, nguon = VIDEO_MAU, [], 'video'
    _proc = subprocess.Popen(['cmd', '/c', str(BAT), src, may_chu, cam, *them], cwd=str(GOC),
                             creationflags=subprocess.CREATE_NEW_CONSOLE)
    _info = dict(source=nguon, camera=cam, started_at=time.time())
    return status()


def stop():
    """Tắt cả cây tiến trình (cmd và python bên trong)."""
    global _proc
    if running():
        subprocess.run(['taskkill', '/PID', str(_proc.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            _proc.wait(5)
        except subprocess.TimeoutExpired:
            pass
    _proc = None
    return status()
