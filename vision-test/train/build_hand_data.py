"""Tạo dữ liệu cho model "có giơ tay không" từ SCB-Dataset.

YOLO tìm người trong ảnh SCB, mỗi người được ghép với nhãn SCB trùng nhiều nhất:
hand-raising -> gio_tay, read/write -> khong. Người không khớp nhãn nào bị bỏ
(SCB không gán nhãn mọi học sinh, nên không thể coi họ là "không giơ").
Ảnh cắt có dạng giống hệt lúc chạy thật: khung người của YOLO, nới 8%, cạnh dài tối đa 320 px.

    python build_hand_data.py <thư mục SCB5-Handrise-...> <thư mục ra>
"""
import random
import sys
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

HERE = Path(__file__).resolve().parent
SCB, OUT = Path(sys.argv[1]), Path(sys.argv[2])
NEG_RATIO = 1.5   # số ảnh "khong" tối đa so với "gio_tay"


def crop_person(im, b, pad=0.08):
    h, w = im.shape[:2]
    x1, y1, x2, y2 = b
    bw, bh = x2 - x1, y2 - y1
    x1, y1 = max(0, int(x1 - pad * bw)), max(0, int(y1 - pad * bh))
    x2, y2 = min(w, int(x2 + pad * bw)), min(h, int(y2 + pad * bh))
    return im[y1:y2, x1:x2]


def iou_parts(p, s):
    ix = max(0, min(p[2], s[2]) - max(p[0], s[0]))
    iy = max(0, min(p[3], s[3]) - max(p[1], s[1]))
    inter = ix * iy
    ap = (p[2] - p[0]) * (p[3] - p[1])
    as_ = (s[2] - s[0]) * (s[3] - s[1])
    return inter / (ap + as_ - inter + 1e-9), inter / (as_ + 1e-9), as_ / (ap + 1e-9)


def main():
    det = YOLO(str(HERE.parent / 'models' / 'yolo26s.pt'))
    rng = random.Random(0)
    for split in ('train', 'val'):
        pos, neg = [], []
        imgs = sorted((SCB / 'images' / split).glob('*.jpg'))
        for k, f in enumerate(imgs):
            lab = SCB / 'labels' / split / (f.stem + '.txt')
            if not lab.exists():
                continue
            im = cv2.imread(str(f))
            if im is None:
                continue
            h, w = im.shape[:2]
            gts = []
            for line in lab.read_text().split('\n'):
                if not line.strip():
                    continue
                c, x, y, bw, bh = map(float, line.split())
                gts.append((int(c), [(x - bw / 2) * w, (y - bh / 2) * h, (x + bw / 2) * w, (y + bh / 2) * h]))
            r = det.predict(im, classes=[0], conf=0.35, imgsz=960, verbose=False)[0]
            persons = r.boxes.xyxy.cpu().numpy()
            # ghép một-một: cặp IoU cao nhất trước
            pairs = []
            for i, p in enumerate(persons):
                for j, (c, s) in enumerate(gts):
                    iou, cover, ratio = iou_parts(p, s)
                    if (iou > 0.35 or (cover > 0.75 and ratio > 0.3)):
                        pairs.append((max(iou, cover * ratio), i, j))
            used_p, used_g = set(), set()
            for _, i, j in sorted(pairs, reverse=True):
                if i in used_p or j in used_g:
                    continue
                used_p.add(i)
                used_g.add(j)
                c = gts[j][0]
                cr = crop_person(im, persons[i])
                if min(cr.shape[:2]) < 24:
                    continue
                s = 320 / max(cr.shape[:2])
                if s < 1:
                    cr = cv2.resize(cr, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
                name = 'gio_tay' if c == 0 else 'khong'
                d = OUT / split / name
                d.mkdir(parents=True, exist_ok=True)
                fn = d / f'scb_{f.stem}_{i}.jpg'
                cv2.imwrite(str(fn), cr)
                (pos if c == 0 else neg).append(fn)
            if k % 500 == 0:
                print(split, k, len(imgs), 'gio_tay', len(pos), 'khong', len(neg), flush=True)
        rng.shuffle(neg)
        for fn in neg[int(len(pos) * NEG_RATIO):]:  # bớt ảnh "khong" cho cân bằng
            fn.unlink()
        neg = neg[:int(len(pos) * NEG_RATIO)]
        print(split, 'xong: gio_tay', len(pos), 'khong', len(neg), flush=True)


if __name__ == '__main__':
    main()
