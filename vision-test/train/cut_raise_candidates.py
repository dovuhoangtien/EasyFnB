"""Cắt ảnh người "có thể đang giơ tay" từ footage để gán nhãn.

Model giơ tay cần ví dụ giơ tay ngoài lớp học (văn phòng, hội thảo, quán, vẫy chào...),
nếu không nó học lối tắt "ảnh lớp học = giơ tay". Khung xương lọc trước: chỉ giữ người
có cổ tay cao hơn vai, để người gán nhãn chỉ phải xem ít ảnh.

    python cut_raise_candidates.py <thư mục clip> <thư mục ảnh ra> <file danh sách ra> [--skip 123 456]
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from easyfnb_test import hand_lift  # noqa: E402
from fnb_common import pad_box, square  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('lst', type=Path)
    ap.add_argument('--skip', nargs='*', default=[], help='mã clip bỏ qua (đã làm rồi)')
    ap.add_argument('--frames', type=int, default=60)
    ap.add_argument('--min-h', type=int, default=60)
    args = ap.parse_args()
    pose = YOLO(str(HERE.parent / 'models' / 'yolo26n-pose.pt'))
    args.out.mkdir(parents=True, exist_ok=True)
    lst = []
    for clip in sorted(args.src.glob('*.mp4')):
        if clip.stem in args.skip:
            continue
        cap = cv2.VideoCapture(str(clip))
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        got = 0
        for fi in np.linspace(0.02 * n, 0.98 * n, args.frames).astype(int):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(fi))
            ok, im = cap.read()
            if not ok:
                continue
            r = pose.predict(im, conf=0.3, imgsz=1280, verbose=False)[0]
            if r.keypoints is None:
                continue
            for k, (b, kp, kc) in enumerate(zip(r.boxes.xyxy.cpu().numpy(), r.keypoints.xy.cpu().numpy(),
                                                r.keypoints.conf.cpu().numpy())):
                if b[3] - b[1] < args.min_h:
                    continue
                lift = hand_lift(kp, kc, b)
                if lift is None or lift <= 0.1:
                    continue
                name = f'{clip.stem}_{fi / fps:.1f}_{k}.jpg'
                cv2.imwrite(str(args.out / name), square(pad_box(im, b, 0.08), 256))
                lst.append(str(args.out / name))
                got += 1
        print(clip.stem, got, flush=True)
    args.lst.write_text('\n'.join(lst), encoding='utf-8')
    print('tổng', len(lst))


if __name__ == '__main__':
    main()
