"""Cắt ảnh bàn và ảnh người từ footage để gán nhãn.

Mỗi clip lấy vài khung cách đều nhau. YOLO tìm "dining table" và "person":
- ảnh bàn: khung bàn nới 10%, kèm số người đang chồng lên bàn (gợi ý cho người gán nhãn)
- ảnh người: khung người nới 8%, chỉ lấy người đủ to (cao từ 120 px)
Tất cả đưa về hình vuông 256 px có viền xám. Ghi danh sách vào meta.csv.

    python cut_crops.py <thư mục footage> <thư mục ra> [--per-clip-frames 6]
"""
import argparse
import csv
import sys
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from fnb_common import pad_box, square  # noqa: E402


def grab(im, b, pad):
    return square(pad_box(im, b, pad), 256)


def overlap(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return ix * iy / ((b[2] - b[0]) * (b[3] - b[1]) + 1e-9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--per-clip-frames', type=int, default=6)
    ap.add_argument('--max-people', type=int, default=4, help='số ảnh người tối đa mỗi khung')
    args = ap.parse_args()
    det = YOLO(str(HERE.parent / 'models' / 'yolo26s.pt'))
    (args.out / 'ban').mkdir(parents=True, exist_ok=True)
    (args.out / 'nguoi').mkdir(parents=True, exist_ok=True)
    rows = []
    clips = sorted(args.src.glob('*.mp4'))
    for ci, clip in enumerate(clips):
        cap = cv2.VideoCapture(str(clip))
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        if n <= 0:
            continue
        for fi in np.linspace(0.08 * n, 0.92 * n, args.per_clip_frames).astype(int):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(fi))
            ok, im = cap.read()
            if not ok:
                continue
            H, W = im.shape[:2]
            r = det.predict(im, classes=[0, 60], conf=0.35, imgsz=960, verbose=False)[0]
            cls = r.boxes.cls.cpu().numpy().astype(int)
            xyxy = r.boxes.xyxy.cpu().numpy()
            conf = r.boxes.conf.cpu().numpy()
            people = [b for b, c in zip(xyxy, cls) if c == 0]
            t = round(fi / fps, 1)
            for k, (b, c, p) in enumerate(zip(xyxy, cls, conf)):
                area = (b[2] - b[0]) * (b[3] - b[1]) / (W * H)
                if c == 60 and area > 0.015:
                    on = sum(overlap(pb, b) > 0.08 for pb in people)
                    name = f'{clip.stem}_{t}_{k}.jpg'
                    cv2.imwrite(str(args.out / 'ban' / name), grab(im, b, 0.10))
                    rows.append(['ban', name, clip.stem, t, round(float(p), 2), round(float(area), 3), on])
            big = sorted([(b[3] - b[1], b, p) for b, c, p in zip(xyxy, cls, conf) if c == 0 and b[3] - b[1] >= 120],
                         key=lambda x: -x[0])[:args.max_people]
            for k, (_, b, p) in enumerate(big):
                name = f'{clip.stem}_{t}_{k}.jpg'
                cv2.imwrite(str(args.out / 'nguoi' / name), grab(im, b, 0.08))
                rows.append(['nguoi', name, clip.stem, t, round(float(p), 2), 0, 0])
        cap.release()
        if ci % 50 == 0:
            print(ci, len(clips), 'ban', sum(r[0] == 'ban' for r in rows), 'nguoi', sum(r[0] == 'nguoi' for r in rows),
                  flush=True)
    with open(args.out / 'meta.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['loai', 'file', 'clip', 't', 'conf', 'dien_tich', 'so_nguoi_tren_ban'])
        w.writerows(rows)
    print('xong', 'ban', sum(r[0] == 'ban' for r in rows), 'nguoi', sum(r[0] == 'nguoi' for r in rows))


if __name__ == '__main__':
    main()
