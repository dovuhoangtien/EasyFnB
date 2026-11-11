"""Cắt ảnh bàn từ clip chấm điểm thành bài kiểm tra cho model sạch/bẩn.

Clip 01: cắt vùng từng bàn ở các đoạn đáp án là T (sạch) hoặc D (bẩn), bước 0,125 s
trong đoạn bẩn (vì ít) và 0,5 s trong đoạn sạch. Clip 03: cả khung hình là một bàn bẩn.
"""
import json
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'anh_ban_test'
zones = json.loads((ROOT / 'zones.json').read_text(encoding='utf-8'))['01_phong_an_goc_cao']['ban']
# đoạn bẩn (D) và sạch (T) của từng bàn, theo dap_an.json
D = {'B1': [(0.0, 0.5)], 'B4': [(0.0, 1.0)], 'B3': [(2.6, 3.1)], 'B2': [(6.1, 6.6)]}
T = {'B1': [(1.25, 15)], 'B2': [(7.25, 15)], 'B3': [], 'B4': [(1.25, 8.6)]}


def table_crop(im, pts, pad=0.10):
    x, y, w, h = cv2.boundingRect(np.array(pts, np.int32))
    H, W = im.shape[:2]
    x1, y1 = max(0, int(x - pad * w)), max(0, int(y - pad * h))
    x2, y2 = min(W, int(x + w + pad * w)), min(H, int(y + h + pad * h))
    return im[y1:y2, x1:x2]


def frame_at(cap, fps, t):
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(t * fps)))
    ok, im = cap.read()
    return im if ok else None


def main():
    for c in ('sach', 'ban'):
        (OUT / c).mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(ROOT / 'clips' / '01_phong_an_goc_cao.mp4'))
    fps = cap.get(cv2.CAP_PROP_FPS)
    n = {'sach': 0, 'ban': 0}
    for label, spans, step in (('ban', D, 0.125), ('sach', T, 0.5)):
        for name, ranges in spans.items():
            for a, b in ranges:
                for t in np.arange(a, b + 1e-6, step):
                    im = frame_at(cap, fps, float(t))
                    if im is None:
                        continue
                    cv2.imwrite(str(OUT / label / f'c01_{name}_{t:.3f}.jpg'), table_crop(im, zones[name]))
                    n[label] += 1
    cap = cv2.VideoCapture(str(ROOT / 'clips' / '03_ban_an_xong_tu_tren.mp4'))
    fps = cap.get(cv2.CAP_PROP_FPS)
    for t in np.arange(0.5, 8.0, 1.0):
        im = frame_at(cap, fps, float(t))
        if im is not None:
            cv2.imwrite(str(OUT / 'ban' / f'c03_{t:.1f}.jpg'), cv2.resize(im, (480, 270)))
            n['ban'] += 1
    print(n)


if __name__ == '__main__':
    main()
