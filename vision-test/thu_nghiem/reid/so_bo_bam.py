"""So nhanh bộ bám người trên clip đông: ByteTrack (không ReID) và BoT-SORT + OSNet (có ReID).

Không có đáp án mã người, nên đo gián tiếp:
- số mã sống >= 2 s: cùng số người thật mà mã nhiều hơn là bị tách mã (mất dấu thành người mới)
- độ dài trung bình một mã
- tốc độ bộ bám (không tính phát hiện người)
và một bảng ảnh: mỗi mã dài 3 ảnh cắt ở đầu, giữa, cuối đời. Ba ảnh khác người là bị tráo mã.

    python thu_nghiem/reid/so_bo_bam.py <video> <bắt đầu s> <số giây> <thư mục ra>
"""
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from boxmot import BotSort, ByteTrack, ReIDConfig
from ultralytics import YOLO

HERE = Path(__file__).resolve().parents[2]


def bo_bam(ten):
    if ten == 'bytetrack':
        return ByteTrack()
    return BotSort(reid=ReIDConfig('osnet-x0-25-msmt17', device='cuda:0', precision='fp16'))


def main():
    video, bd, dai, ra = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), Path(sys.argv[4])
    ra.mkdir(parents=True, exist_ok=True)
    det = YOLO(str(HERE / 'models' / 'yolo26n-pose_544x960_fp16.engine'), task='pose')
    cap = cv2.VideoCapture(video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(bd * fps))
    # phát hiện người một lần, các bộ bám dùng chung đầu vào
    frames, dets = [], []
    for _ in range(int(dai * fps)):
        ok, f = cap.read()
        if not ok:
            break
        r = det.predict(f, imgsz=(544, 960), conf=0.25, verbose=False, half=True)[0]
        b = r.boxes
        d = np.concatenate([b.xyxy.cpu().numpy(), b.conf.cpu().numpy()[:, None], np.zeros((len(b), 1))], 1) \
            if len(b) else np.zeros((0, 6))
        frames.append(f)
        dets.append(d.astype(np.float32))
    print(f'{Path(video).stem}: {len(frames)} khung, trung bình {np.mean([len(d) for d in dets]):.1f} người/khung')

    kq = {}
    for ten in ('bytetrack', 'botsort_osnet'):
        tr = bo_bam(ten)
        song = defaultdict(list)   # mã -> [(khung, box)]
        t0 = time.perf_counter()
        for k, (f, d) in enumerate(zip(frames, dets)):
            o = np.asarray(tr.update(d, f))
            for row in o.reshape(-1, o.shape[-1] if o.size else 8):
                song[int(row[4])].append((k, row[:4].tolist()))
        dt = time.perf_counter() - t0
        dai_ = {i: v for i, v in song.items() if len(v) >= 2 * fps}
        kq[ten] = dict(ma=len(song), ma_2s=len(dai_), do_dai_tb_s=round(np.mean([len(v) for v in dai_.values()]) / fps, 1)
                       if dai_ else 0, ms_khung=round(1000 * dt / max(1, len(frames)), 1))
        print(ten, kq[ten])
        # bảng ảnh: 24 mã sống lâu nhất, mỗi mã 3 ảnh
        hang = []
        for i in sorted(dai_, key=lambda i: -len(dai_[i]))[:24]:
            v = dai_[i]
            o3 = []
            for k, box in (v[0], v[len(v) // 2], v[-1]):
                x1, y1, x2, y2 = [int(max(0, c)) for c in box]
                c = frames[k][y1:y2, x1:x2]
                c = cv2.resize(c, (64, 128)) if c.size else np.full((128, 64, 3), 255, np.uint8)
                o3.append(c)
            the = np.hstack(o3)
            the = cv2.copyMakeBorder(the, 18, 2, 2, 2, cv2.BORDER_CONSTANT, value=(255, 255, 255))
            cv2.putText(the, f'#{i} {len(v) / fps:.0f}s', (3, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
            hang.append(the)
        if hang:
            hang += [np.full_like(hang[0], 255)] * (-len(hang) % 6)
            cv2.imwrite(str(ra / f'{Path(video).stem}_{ten}.jpg'),
                        np.vstack([np.hstack(hang[j:j + 6]) for j in range(0, len(hang), 6)]))
    (ra / f'{Path(video).stem}.json').write_text(json.dumps(kq, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
