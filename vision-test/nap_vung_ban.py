#!/usr/bin/env python
"""Nạp vùng bàn vẽ sẵn của một clip mẫu lên máy chủ, để chạy demo không phải vẽ tay.

zones.json khoá theo tên tệp clip (dùng khi chạy offline). Khi chạy như camera thật
(chay_camera.bat), pipeline lấy vùng bàn từ máy chủ theo mã camera, nên phải đẩy
vùng của clip lên trước. Lệnh này làm việc đó:

    python nap_vung_ban.py m01_bbq_vn_ban_an
    python nap_vung_ban.py m03_cafe_san_vuon_vn http://172.21.1.8:8080 cam1

Chỉ nạp khi zones.json có mục cho clip; clip không có thì giữ nguyên vùng đang có
trên máy chủ và in nhắc vẽ tay.
"""
import argparse
import json
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent


def kich_thuoc_video(path):
    """Rộng, cao của khung hình đầu tiên (vùng bàn lưu theo pixel của khung này)."""
    import cv2
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise SystemExit(f'Không mở được video: {path}')
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    if not w or not h:
        raise SystemExit(f'Không đọc được kích thước khung hình: {path}')
    return w, h


def gui(url, body):
    data = json.dumps(body, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='PUT',
                                 headers={'Content-Type': 'application/json'})
    ctx = ssl._create_unverified_context() if url.startswith('https://') else None
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        return json.loads(r.read().decode('utf-8'))


def main():
    ap = argparse.ArgumentParser(description='Nạp vùng bàn của clip mẫu lên máy chủ')
    ap.add_argument('clip', help='tên clip trong zones.json, ví dụ m01_bbq_vn_ban_an')
    ap.add_argument('may_chu', nargs='?', default='http://localhost:8080')
    ap.add_argument('--camera', default='cam1')
    ap.add_argument('--zones', type=Path, default=HERE / 'zones.json')
    a = ap.parse_args()

    zones = json.loads(a.zones.read_text(encoding='utf-8')) if a.zones.exists() else {}
    cfg = zones.get(a.clip) or {}
    ban = cfg.get('ban') or {}
    if not ban:
        print(f'  zones.json chưa có vùng bàn cho {a.clip}: vẽ tay ở trang cai-dat của camera {a.camera}.')
        return 0

    video = HERE / 'video_mang' / f'{a.clip}.mp4'
    if not video.exists():
        video = HERE / 'clips' / f'{a.clip}.mp4'
    if not video.exists():
        print(f'  không thấy video của {a.clip} để lấy kích thước khung hình; bỏ qua.')
        return 0
    w, h = kich_thuoc_video(video)

    body = dict(camera=a.camera, frame_w=w, frame_h=h,
                tables=[dict(id=k, polygon=v) for k, v in ban.items()])
    url = a.may_chu.rstrip('/') + '/api/zones'
    try:
        r = gui(url, body)
    except urllib.error.URLError as exc:
        print(f'  máy chủ chưa chạy ({exc}); vùng bàn sẽ phải vẽ tay sau khi mở máy chủ.')
        return 0
    n = len(r.get('tables') or [])
    print(f'  đã nạp {n} vùng bàn của {a.clip} cho camera {a.camera} ({w}×{h})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
